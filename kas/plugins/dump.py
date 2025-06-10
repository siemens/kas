# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2024
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
    files. The output of this command can be used to further analyze the build
    configuration.

    When running with ``--lock``, a locking spec is created which only contains
    the exact commit of each repository. This can be used to pin the commit of
    floating branches and tags, while still keeping an easy update path. For
    details on the locking support, see :class:`kas.plugins.lock`.

    .. note::
        The options to create and update lock files have been moved to the lock
        plugin.

    When running with ``--resolve-local``, VCS tracking information of the root
    repo (the one with the kas-project.yml) is added to the output. The
    generated file can be used as single input to kas to reproduce the build
    environment. If the root repo is not under version control or contains
    uncommitted changes, a warning is emitted.

    Please note:

    - the dumped config is semantically identical but not bit-by-bit identical
    - all referenced repositories are checked out to resolve cross-repo configs
    - all branches are resolved before patches are applied
    - the ordering of the keys is kept unless ``--sort`` is used. If you intend
      to store the flattened configs for comparison, it is recommended to sort
      the keys.

    For example, to get a single config representing the final build config of
    ``kas-project.yml:target-override.yml`` you could run::

        kas dump kas-project.yml:target-override.yml > kas-project-expanded.yml

    The generated config can be used as input for kas::

        kas build kas-project-expanded.yml
"""

import sys
import json
import yaml
import logging
import argparse
from typing import TypeVar, TextIO
from collections import OrderedDict
from kas.context import get_context
from kas.plugins.checkout import Checkout
from kas.kasusererror import KasUserError, ArgsCombinationError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2022'

LOCKFILE_VERSION_MIN = 14
SCHEMA_VERSION_MIN = 7


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

    @staticmethod
    def setup_parser_format_args(parser):
        parser.add_argument('--indent',
                            type=int,
                            default=4,
                            help='Line indent (# of spaces, default: 4)')
        parser.add_argument('--sort',
                            action='store_true',
                            default=False,
                            help='Alphanumerically sort keys in output')

    @classmethod
    def setup_parser(cls, parser):
        super().setup_parser(parser)
        Dump.setup_parser_format_args(parser)
        lk_or_env = parser.add_mutually_exclusive_group()
        parser.add_argument('--format',
                            choices=['yaml', 'json'],
                            default='yaml',
                            help='Output format (default: yaml)')
        parser.add_argument('--resolve-refs',
                            action='store_true',
                            help='Replace floating refs with exact SHAs. '
                                 'Overrides are removed')
        parser.add_argument('--resolve-local',
                            action='store_true',
                            help='Add tracking information of root repo')
        lk_or_env.add_argument('--resolve-env',
                               action='store_true',
                               help='Set env defaults to captured env value')
        lk_or_env.add_argument('--lock',
                               action='store_true',
                               help='Create lockfile with exact SHAs')
        parser.add_argument('-i', '--inplace',
                            action='store_true',
                            help=argparse.SUPPRESS)

    @staticmethod
    def dump_config(config: dict, target: IoTarget, format: str, indent: int,
                    sorted: bool):
        """
        Dump the configuration to the target in the specified format.
        """
        with IoTargetMonitor(target) as f:
            if format == 'json':
                json.dump(config, f, indent=indent, sort_keys=sorted)
                f.write('\n')
            elif format == 'yaml':
                yaml.dump(
                    config, f,
                    indent=indent,
                    sort_keys=sorted,
                    Dumper=Dump.KasYamlDumper)
            else:
                raise OutputFormatError(format)

    def run(self, args):
        def _filter_enabled(repos):
            return [(k, r) for k, r in repos if not r.operations_disabled]

        def _filter_local(repos):
            return [(k, r) for k, r in repos
                    if r.operations_disabled and r.name]

        args.skip += [
            'setup_dir',
            'repos_apply_patches',
            'setup_environ',
            'write_bbconfig',
        ]

        super().run(args)
        ctx = get_context()
        schema_v = LOCKFILE_VERSION_MIN if args.lock else SCHEMA_VERSION_MIN
        config_expanded = {'header': {'version': schema_v}} if args.lock \
            else ctx.config.get_config(remove_includes=True)
        repos = ctx.config.repo_dict.items()
        output = IoTarget(target=sys.stdout, managed=False)

        if args.inplace and not args.lock:
            raise ArgsCombinationError('--inplace requires --lock')
        if args.resolve_local and args.lock:
            raise ArgsCombinationError(
                '--resolve-local cannot be used with --lock')
        if args.inplace and args.lock:
            from kas.plugins.lock import Lock
            logging.warning('The --inplace option is deprecated. '
                            'Migrate to the "lock" command.')
            return Lock().run(args)

        if args.lock:
            args.resolve_refs = True
            # when locking, only consider repos managed by kas
            repos = _filter_enabled(repos)
            config_expanded['overrides'] = \
                {'repos': {k: {'commit': r.revision} for k, r in repos}}

        if args.resolve_refs and not args.lock:
            for k, r in _filter_enabled(repos):
                if r.commit or r.branch or r.tag:
                    config_expanded['repos'][k]['commit'] = r.revision
                elif r.refspec:
                    config_expanded['repos'][k]['refspec'] = r.revision
            # as the refs are resolved, the overrides are redundant
            if 'overrides' in config_expanded:
                del config_expanded['overrides']

        if args.resolve_local:
            for k, r in _filter_local(repos):
                if r.revision:
                    if r.dirty:
                        logging.warning(f'Repository {r.name} (root repo) '
                                        'contains uncommitted changes.')
                    if config_expanded['repos'][k] is None:
                        config_expanded['repos'][k] = {}
                    config_expanded['repos'][k]['url'] = r.url
                    config_expanded['repos'][k]['commit'] = r.revision
                else:
                    logging.warning(f'Repository {r.name} (root repo) '
                                    'is not under version control.')

        if args.resolve_env and 'env' in config_expanded:
            config_expanded['env'] = ctx.config.get_environment()

        self.dump_config(config_expanded, output, args.format, args.indent,
                         args.sort)


__KAS_PLUGINS__ = [Dump]
