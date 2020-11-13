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
    This plugin implements the ``kas shell`` command.

    When this command is executed, kas will checkout repositories, setup the
    build environment and then start a shell in the build environment. This
    can be used to manually run ``bitbake`` with custom command line options
    or to execute other commands such as ``runqemu``.

    For example, to start a shell in the build environment for the file
    ``kas-project.yml`` you could run::

        kas shell kas-project.yml

    Or to invoke qemu to test an image which has been built::

        kas shell kas-project.yml -c 'runqemu'
"""

import logging
import subprocess
import sys
from kas.context import create_global_context
from kas.config import Config
from kas.libcmds import Macro, Command

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
        ctx.config = Config(args.config)

        if args.keep_config_unchanged:
            # Skip the tasks which would change the config of the build
            # environment
            args.skip += [
                'setup_dir',
                'finish_setup_repos',
                'repos_apply_patches',
                'write_bbconfig',
            ]

        macro = Macro()
        macro.add(ShellCommand(args.command))
        macro.run(ctx, args.skip)


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
        ret = subprocess.call(cmd, env=ctx.environ, cwd=ctx.build_dir)
        if ret != 0:
            logging.error('Shell returned non-zero exit status %d', ret)
            sys.exit(ret)


__KAS_PLUGINS__ = [Shell]
