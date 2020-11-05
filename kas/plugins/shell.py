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

import logging
import os
import subprocess
import sys
from kas.context import create_global_context
from kas.config import Config
from kas.libcmds import (Macro, Command, SetupDir, SetupEnviron,
                         WriteBBConfig, SetupHome, ReposApplyPatches,
                         CleanupSSHAgent, SetupSSHAgent,
                         Loop, InitSetupRepos, FinishSetupRepos,
                         SetupReposStep)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Shell:
    """
        Implements a kas plugin that opens a shell within the kas environment.
    """

    name = 'shell'
    helpmsg = 'Run a shell in the build environment.'

    @classmethod
    def setup_parser(cls, parser):
        """
            Setup the argument parser for the shell plugin
        """

        parser.add_argument('-k', '--keep-config-unchanged',
                            help='Skip steps that change the configuration',
                            action='store_true')
        parser.add_argument('-c', '--command',
                            help='Run command',
                            default='')

    def run(self, args):
        """
            Runs this kas plugin
        """

        ctx = create_global_context(args)
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


class ShellCommand(Command):
    """
        This class implements the command that starts a shell.
    """

    def __init__(self, cmd):
        """
        Initialize the cmd.

        Args:
            self: (todo): write your description
            cmd: (int): write your description
        """
        super().__init__()
        self.cmd = []
        if cmd:
            self.cmd = cmd

    def __str__(self):
        """
        Return a string representation of this object.

        Args:
            self: (todo): write your description
        """
        return 'shell'

    def execute(self, ctx):
        """
        Execute the command.

        Args:
            self: (todo): write your description
            ctx: (todo): write your description
        """
        cmd = [ctx.environ.get('SHELL', '/bin/sh')]
        if self.cmd:
            cmd.append('-c')
            cmd.append(self.cmd)
        ret = subprocess.call(cmd, env=ctx.environ, cwd=ctx.build_dir)
        if ret != 0:
            logging.error('Shell returned non-zero exit status %d', ret)
            sys.exit(ret)


__KAS_PLUGINS__ = [Shell]
