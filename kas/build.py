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
    The build plugin for kas.
"""

import logging
import os
import subprocess
import sys
from .context import create_global_context
from .config import Config
from .libkas import find_program, run_cmd, kasplugin
from .libcmds import (Macro, Command, SetupDir, CleanupSSHAgent,
                      SetupSSHAgent, SetupEnviron,
                      WriteBBConfig, SetupHome, ReposApplyPatches,
                      Loop, InitSetupRepos, FinishSetupRepos,
                      SetupReposStep)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


@kasplugin
class Build:
    """
        This class implements the build plugin for kas.
    """

    @classmethod
    def get_argparser(cls, parser):
        """
            Returns an a parser for the build plugin
        """
        bld_psr = parser.add_parser('build',
                                    help='Checks out all necessary '
                                    'repositories and builds using '
                                    'bitbake as specificed in the '
                                    'configuration file.')

        bld_psr.add_argument('config',
                             help='Config file')
        bld_psr.add_argument('--target',
                             action='append',
                             help='Select target to build')
        bld_psr.add_argument('-c', '--cmd', '--task', dest='task',
                             help='Select which task should be executed')
        bld_psr.add_argument('--skip',
                             help='Skip build steps',
                             default=[])

    def run(self, args):
        """
            Executes the build command of the kas plugin.
        """

        if args.cmd != 'build':
            return False

        ctx = create_global_context()
        ctx.config = Config(args.config, args.target, args.task)

        macro = Macro()

        # Prepare
        macro.add(SetupDir())

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(SetupSSHAgent())

        macro.add(InitSetupRepos())

        repo_loop = Loop('repo_setup_loop')
        repo_loop.add(SetupReposStep())

        macro.add(repo_loop)
        macro.add(FinishSetupRepos())

        macro.add(SetupEnviron())
        macro.add(SetupHome())
        macro.add(ReposApplyPatches())

        macro.add(WriteBBConfig())

        # Build
        macro.add(BuildCommand(args.task))

        if 'SSH_PRIVATE_KEY' in os.environ:
            macro.add(CleanupSSHAgent())

        macro.run(ctx, args.skip)

        return True


class BuildCommand(Command):
    """
        Implements the bitbake build step.
    """

    def __init__(self, task):
        super().__init__()
        self.task = task

    def __str__(self):
        return 'build'

    def execute(self, ctx):
        """
            Executes the bitbake build command.
        """
        # Start bitbake build of image
        bitbake = find_program(ctx.environ['PATH'], 'bitbake')
        cmd = ([bitbake, '-k', '-c', ctx.config.get_bitbake_task()]
               + ctx.config.get_bitbake_targets())
        if sys.stdout.isatty():
            logging.info('%s$ %s', ctx.build_dir, ' '.join(cmd))
            subprocess.call(cmd, env=ctx.environ, cwd=ctx.build_dir)
        else:
            run_cmd(cmd, cwd=ctx.build_dir)
