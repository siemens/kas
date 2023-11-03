# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2023
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
    This plugin implements the ``kas dump`` command.

    When this command is executed in default mode, kas will parse all
    referenced config files, expand includes and print a flattened yaml version
    of the configuration to stdout. This config is semantically identical to
    the input, but does not include any references to other configuration
    files. The output of this command can be used to further analyse the build
    configuration.

    When running with ``--lock``, a locking spec is created which only contains
    the exact commit of each repository. This can be used to pin the commit of
    floating branches and tags, while still keeping an easy update path. When
    combining with ``--inplace``, a lockfile is created next to the first file
    on the kas cmdline. For details on the locking support, see
    :class:`kas.includehandler.IncludeHandler`.

    Please note:

    - the dumped config is semantically identical but not bit-by-bit identical
    - all referenced repositories are checked out to resolve cross-repo configs
    - all branches are resolved before patches are applied

    For example, to get a single config representing the final build config of
    ``kas-project.yml:target-override.yml`` you could run::

        kas dump kas-project.yml:target-override.yml > kas-project-expanded.yml

    The generated config can be used as input for kas::

        kas build kas-project-expanded.yml

    Example of the locking mechanism (call again to regenerate lockfile).
    The lockfile is created as ``kas-project.lock.yml``::

        kas dump --lock --inplace --update kas-project.yml

    The generated lockfile will automatically be used to pin the revisions::

        kas build kas-project.yml

    Note, that the lockfiles should be checked-in into the VCS.
"""

import sys
import json
import yaml
from typing import TypeVar, TextIO
from collections import OrderedDict
from kas.context import get_context
from kas.plugins.checkout import Checkout
from kas.kasusererror import KasUserError, ArgsCombinationError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2022'


class OutputFormatError(KasUserError):
    def __init__(self, format):
        super().__init__(f'invalid format {format}')


class IoTarget:
    StrOrTextIO = TypeVar('StrOrTextIO', str, TextIO)

    target: StrOrTextIO
    managed: bool

    def __init__(self, target, managed):
        self.target = target
        self.managed = managed


class IoTargetMonitor:
    """
    Simple monitor to unify access to file targets that need
    to be closed (files) and ambient ones (stdout / stderr)
    """

    def __init__(self, target: IoTarget):
        self._target = target
        self._file = None

    def __enter__(self):
        if self._target.managed:
            self._file = open(self._target.target, 'w')
            return self._file
        return self._target.target

    def __exit__(self, exc_type, exc_value, traceback):
        if self._target.managed:
            self._file.close()


class Dump(Checkout):
    """
    Implements a kas plugin that combines multiple kas configurations
    and dumps the result.
    """

    name = 'dump'
    helpmsg = (
        'Expand and dump the final config to stdout. When resolving branches, '
        'this is done before patches are applied.'
    )

    class KasYamlDumper(yaml.Dumper):
        """
        Yaml formatter (dumper) that generates output in a formatting which
        is similar to kas example input files.
        """

        def represent_data(self, data):
            if isinstance(data, str):
                if data.count('\n') > 0:
                    return self.represent_scalar(
                        'tag:yaml.org,2002:str',
                        data,
                        style='|')
                return self.represent_scalar('tag:yaml.org,2002:str', data)
            elif isinstance(data, OrderedDict):
                return self.represent_mapping(
                    'tag:yaml.org,2002:map',
                    data.items())
            elif data is None:
                return self.represent_scalar('tag:yaml.org,2002:null', '')
            return super().represent_data(data)

    @classmethod
    def setup_parser(cls, parser):
        super().setup_parser(parser)
        lk_or_env = parser.add_mutually_exclusive_group()
        parser.add_argument('--format',
                            choices=['yaml', 'json'],
                            default='yaml',
                            help='Output format (default: yaml)')
        parser.add_argument('--indent',
                            type=int,
                            default=4,
                            help='Line indent (# of spaces, default: 4)')
        parser.add_argument('--resolve-refs',
                            action='store_true',
                            help='Replace floating refs with exact SHAs')
        lk_or_env.add_argument('--resolve-env',
                               action='store_true',
                               help='Set env defaults to captured env value')
        lk_or_env.add_argument('--lock',
                               action='store_true',
                               help='Create lockfile with exact SHAs')
        parser.add_argument('-i', '--inplace',
                            action='store_true',
                            help='Update lockfile in-place (requires --lock)')

    def run(self, args):
        args.skip += [
            'setup_dir',
            'repos_apply_patches',
            'setup_environ',
            'write_bbconfig',
        ]

        super().run(args)
        ctx = get_context()
        schema_v = 14 if args.lock else 7
        config_expanded = {'header': {'version': schema_v}} if args.lock \
            else ctx.config.get_config()
        repos = ctx.config.get_repos()
        output = IoTarget(target=sys.stdout, managed=False)

        if args.inplace and not args.lock:
            raise ArgsCombinationError('--inplace requires --lock')

        if args.lock:
            args.resolve_refs = True
            # when locking, only consider repos managed by kas
            repos = [r for r in repos if not r.operations_disabled]
            config_expanded['overrides'] = \
                {'repos': {r.name: {'commit': r.revision} for r in repos}}

        if args.lock and args.inplace:
            lockfile = ctx.config.handler.get_lockfile()
            output = IoTarget(target=lockfile, managed=True)

        # includes are already expanded, delete the key
        if 'includes' in config_expanded['header']:
            del config_expanded['header']['includes']

        if args.resolve_refs and not args.lock:
            for r in repos:
                if r.commit or r.branch or r.tag:
                    config_expanded['repos'][r.name]['commit'] = r.revision
                elif r.refspec:
                    config_expanded['repos'][r.name]['refspec'] = r.revision

        if args.resolve_env and 'env' in config_expanded:
            config_expanded['env'] = ctx.config.get_environment()

        with IoTargetMonitor(output) as f:
            if args.format == 'json':
                json.dump(config_expanded, f, indent=args.indent)
                f.write('\n')
            elif args.format == 'yaml':
                yaml.dump(
                    config_expanded, f,
                    indent=args.indent,
                    Dumper=self.KasYamlDumper)
            else:
                raise OutputFormatError(args.format)


__KAS_PLUGINS__ = [Dump]
