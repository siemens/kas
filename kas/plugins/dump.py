# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2022
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

    When this command is executed, kas will parse all referenced config
    files, expand includes and print a flattened yaml version of the
    configuration to stdout. This config is semantically identical to the
    input, but does not include any references to other configuration files.
    The output of this command can be used to further analyse the build
    configuration.

    Please note:

    - the dumped config is semantically identical but not bit-by-bit identical
    - all referenced repositories are checked out to resolve cross-repo configs
    - all refspecs are resolved before patches are applied

    For example, to get a single config representing the final build config of
    ``kas-project.yml:target-override.yml`` you could run:

        kas dump kas-project.yml:target-override.yml > kas-project-expanded.yml

    The generated config can be used as input for kas:

        kas build kas-project-expanded.yml
"""

import logging
import sys
import json
import yaml
from collections import OrderedDict
from kas.context import get_context
from kas.plugins.checkout import Checkout

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2022'


class Dump(Checkout):
    """
    Implements a kas plugin that combines multiple kas configurations
    and dumps the result.
    """

    name = 'dump'
    helpmsg = (
        'Expand and dump the final config to stdout. When resolving refspecs, '
        'these are resolved before patches are applied.'
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
        parser.add_argument('--resolve-env',
                            action='store_true',
                            help='Set env defaults to captured env value')

    def run(self, args):
        args.skip += [
            'setup_dir',
            'repos_apply_patches',
            'setup_environ',
            'write_bbconfig',
        ]

        super().run(args)
        ctx = get_context()
        config_expanded = ctx.config.get_config()

        # includes are already expanded, delete the key
        if 'includes' in config_expanded['header']:
            del config_expanded['header']['includes']

        if args.resolve_refs:
            repos = ctx.config.get_repos()
            for r in repos:
                if r.refspec:
                    config_expanded['repos'][r.name]['refspec'] = r.revision

        if args.resolve_env and 'env' in config_expanded:
            config_expanded['env'] = ctx.config.get_environment()

        if args.format == 'json':
            json.dump(config_expanded, sys.stdout, indent=args.indent)
            sys.stdout.write('\n')
        elif args.format == 'yaml':
            yaml.dump(
                config_expanded, sys.stdout,
                indent=args.indent,
                Dumper=self.KasYamlDumper)
        else:
            logging.error('invalid format %s', args.format)
            sys.exit(1)


__KAS_PLUGINS__ = [Dump]
