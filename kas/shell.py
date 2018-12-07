# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2018
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
    This module contains a kas plugin that opens a shell within the kas
    environment
"""

import subprocess
import os
from .libkas import kasplugin
from .context import create_global_context
from .config import Config
from .libcmds import (Macro, Command, SetupDir, SetupEnviron,
                      WriteBBConfig, SetupHome, ReposApplyPatches,
                      CleanupSSHAgent, SetupSSHAgent,
                      Loop, InitSetupRepos, FinishSetupRepos,
                      SetupReposStep)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


@kasplugin
class Shell:
    """
        Implements a kas plugin that opens a shell within the kas environment.
    """

    @classmethod
    def get_argparser(cls, parser):
        """
            Returns a parser for the shell plugin
        """
        sh_prs = parser.add_parser('shell',
                                   help='Run a shell in the build '
                                   'environment.')

        sh_prs.add_argument('config',
                            help='Config file')
        sh_prs.add_argument('--skip',
                            help='Skip build steps',
                            default=[])
        sh_prs.add_argument('-k', '--keep-config-unchanged',
                            help='Skip steps that change the configuration',
                            action='store_true')
        sh_prs.add_argument('-c', '--command',
                            help='Run command',
                            default='')

    def run(self, args):
        """
            Runs this kas plugin
        """

        if args.cmd != 'shell':
            return False

        ctx = create_global_context()
        ctx.config = Config(args.config, None, None)

        macro = Macro()

        # Prepare
        if not args.keep_config_unchanged:
            macro.add(SetupDir())

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(SetupSSHAgent())

        ctx.keep_config = args.keep_config_unchanged

        macro.add(InitSetupRepos())

        repo_loop = Loop('repo_setup_loop')
        repo_loop.add(SetupReposStep())

        macro.add(repo_loop)
        macro.add(FinishSetupRepos())

        macro.add(SetupEnviron())
        macro.add(SetupHome())

        if not args.keep_config_unchanged:
            macro.add(ReposApplyPatches())
            macro.add(WriteBBConfig())

        # Shell
        macro.add(ShellCommand(args.command))

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(CleanupSSHAgent())

        macro.run(ctx, args.skip)

        return True


class ShellCommand(Command):
    """
        This class implements the command that starts a shell.
    """

    def __init__(self, cmd):
        super().__init__()
        self.cmd = []
        if cmd:
            self.cmd = cmd

    def __str__(self):
        return 'shell'

    def execute(self, ctx):
        cmd = [ctx.environ.get('SHELL', '/bin/sh')]
        if self.cmd:
            cmd.append('-c')
            cmd.append(self.cmd)
        subprocess.call(cmd, env=ctx.environ,
                        cwd=ctx.build_dir)
