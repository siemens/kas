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
    This plugin implements the ``kas build`` command.

    When this command is executed, kas will checkout repositories, setup the
    build environment and then invoke bitbake to build the targets selected
    in the chosen config file.

    When running with ``--provenance <true|mode=...>`` kas will generate an
    provenance attestation for the build. The attestation will be stored in
    ``attestation/kas-build.provenance.json`` in the build directory.
    For details about provenance, see the build attestation chapter.

    .. note::
        In provenance mode, the command returns with a non-zero exit
        code in case no artifact is found for at least one entry.
"""

import logging
import subprocess
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from kas.context import create_global_context
from kas.config import Config
from kas.libkas import find_program, run_cmd_async
from kas.libkas import setup_parser_keep_config_unchanged_arg
from kas.libcmds import Macro, Command
from kas.libkas import setup_parser_common_args, setup_parser_config_arg
from kas.kasusererror import CommandExecError
from kas.attestation import Provenance, Statement


__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2024'


class Build:
    """
        This class implements the build plugin for kas.
    """

    name = 'build'
    helpmsg = (
        'Checks out all necessary repositories and builds using bitbake as '
        'specified in the configuration file.'
    )

    @classmethod
    def setup_parser(cls, parser):
        """
            Setup the argument parser for the build plugin
        """

        setup_parser_common_args(parser)
        setup_parser_config_arg(parser)
        setup_parser_keep_config_unchanged_arg(parser)
        parser.add_argument('extra_bitbake_args',
                            nargs='*',
                            help='Extra arguments to pass to bitbake '
                                 '(typically requires separation via \'--\')')
        parser.add_argument('--target',
                            action='append',
                            help='Select target to build')
        parser.add_argument('-c', '--cmd', '--task', dest='task',
                            help='Select which task should be executed')
        parser.add_argument('--provenance',
                            choices=['true', 'mode=min', 'mode=max'],
                            help='Enable provenance attestation generation')

    def run(self, args):
        """
            Executes the build command of the kas plugin.
        """

        if args.config and args.config.startswith('-'):
            args.extra_bitbake_args.insert(0, args.config)
            args.config = None

        ctx = create_global_context(args)
        ctx.config = Config(ctx, args.config, args.target, args.task)

        macro = Macro()
        macro.add(BuildCommand(args.extra_bitbake_args))
        macro.run(ctx, args.skip)


class BuildCommand(Command):
    """
        Implements the bitbake build step.
    """

    def __init__(self, extra_bitbake_args):
        super().__init__()
        self.extra_bitbake_args = extra_bitbake_args

    def __str__(self):
        return 'build'

    def _generate_attestation(self, ctx,
                              time_started, time_finished,
                              mode):
        """
            Generate the provenance attestation for the build.
        """
        predicate = Provenance(ctx, time_started, time_finished,
                               mode)
        stmt = Statement(predicate, ctx, time_started, time_finished).as_dict()
        att_dir = Path(ctx.build_dir) / 'attestation'
        att_dir.mkdir(parents=True, exist_ok=True)
        with open(att_dir / 'kas-build.provenance.json', 'w') as f:
            f.write(json.dumps(stmt, indent=4))
            f.write('\n')

    def execute(self, ctx):
        """
            Executes the bitbake build command.
        """
        # Start bitbake build of image
        bitbake = find_program(ctx.environ['PATH'], 'bitbake')
        cmd = [bitbake, '-c', ctx.config.get_bitbake_task()] \
            + self.extra_bitbake_args + ctx.config.get_bitbake_targets()

        time_started = datetime.now()
        if sys.stdout.isatty():
            logging.info('%s$ %s', ctx.build_dir, ' '.join(cmd))
            ret = subprocess.call(cmd, env=ctx.environ, cwd=ctx.build_dir)
            if ret != 0:
                raise CommandExecError(cmd, ret)
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_cmd_async(cmd, cwd=ctx.build_dir,
                                                  liveupdate=True))
        time_finished = datetime.now()

        if ctx.args.provenance:
            mode = Provenance.Mode.MAX if ctx.args.provenance == 'mode=max' \
                else Provenance.Mode.MIN
            self._generate_attestation(ctx, time_started, time_finished, mode)


__KAS_PLUGINS__ = [Build]
