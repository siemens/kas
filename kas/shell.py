# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017
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
from kas.libkas import kasplugin
from kas.config import Config
from kas.libcmds import (Macro, Command, SetupDir, SetupProxy, SetupEnviron,
                         WriteConfig, SetupHome, ReposFetch, ReposCheckout,
                         CleanupSSHAgent, SetupSSHAgent)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


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
        sh_prs.add_argument('--target',
                            action='append',
                            help='Select target to build')
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
        # pylint: disable= no-self-use

        if args.cmd != 'shell':
            return False

        cfg = Config(args.config, args.target)

        macro = Macro()

        # Prepare
        if not args.keep_config_unchanged:
            macro.add(SetupDir())

        macro.add(SetupProxy())

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(SetupSSHAgent())

        if not args.keep_config_unchanged:
            macro.add(ReposFetch())
            macro.add(ReposCheckout())
            macro.add(SetupEnviron())
            macro.add(WriteConfig())
        else:
            macro.add(SetupEnviron())

        # Shell
        macro.add(SetupHome())
        macro.add(ShellCommand(args.command))

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(CleanupSSHAgent())

        macro.run(cfg, args.skip)

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

    def execute(self, config):
        cmd = [config.environ.get('SHELL', '/bin/sh')]
        if self.cmd:
            cmd.append('-c')
            cmd.append(self.cmd)
        subprocess.call(cmd, env=config.environ,
                        cwd=config.build_dir)
