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
    This plugin implements the ``kas lock`` command.

    When this command is executed a locking spec is created which only contains
    the exact commit of each repository. This is used to pin the commit of
    floating branches and tags, while still keeping an easy update path. The
    lockfile is created next to the first file on the kas cmdline. For details
    on the locking support, see :class:`kas.includehandler.IncludeHandler`.

    Please note:

    - all referenced repositories are checked out to resolve cross-repo configs
    - all branches are resolved before patches are applied

    Example (call again to regenerate lockfile).
    The lockfile is created as ``kas-project.lock.yml``::

        kas lock --update kas-project.yml

    The generated lockfile will automatically be used to pin the revisions::

        kas build kas-project.yml

    Note, that the lockfiles should be checked-in into the VCS.
"""

import logging
import os
from kas.context import get_context
from kas.plugins.checkout import Checkout
from kas.plugins.dump import Dump, IoTarget

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2024'


class Lock(Checkout):
    """
    Implements a kas plugin to create and update kas project lockfiles.
    """

    name = 'lock'
    helpmsg = (
        'Create and update kas project lockfiles.'
    )

    @classmethod
    def setup_parser(cls, parser):
        super().setup_parser(parser)
        Dump.setup_parser_format_args(parser)

    def run(self, args):
        def _filter_enabled(repos):
            return [(k, r) for k, r in repos if not r.operations_disabled]

        args.skip += [
            'setup_dir',
            'repos_apply_patches',
            'setup_environ',
            'write_bbconfig',
        ]

        super().run(args)
        ctx = get_context()
        config_expanded = {'header': {'version': 14}}
        repos = ctx.config.repo_dict.items()

        # when locking, only consider repos managed by kas
        repos = _filter_enabled(repos)
        config_expanded['overrides'] = \
            {'repos': {k: {'commit': r.revision} for k, r in repos}}

        lockfile = ctx.config.handler.get_lockfile()
        output = IoTarget(target=lockfile, managed=True)
        format = "json" if lockfile.suffix == '.json' else "yaml"

        Dump.dump_config(config_expanded, output, format,
                         args.indent, args.sort)
        logging.info('Lockfile created: %s',
                     os.path.relpath(lockfile, os.getcwd()))


__KAS_PLUGINS__ = [Lock]
