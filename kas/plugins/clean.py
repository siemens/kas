# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens, 2025
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
    This plugin implements the ``kas {clean,cleansstate,cleanall}``
    commands. In case a configuration file is provided, it will be used to
    determine the build system and the files managed by kas.
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from kas.context import create_global_context, get_context
from kas.config import Config, CONFIG_YAML_FILE
from kas.libcmds import Macro

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens, 2025'


class Clean():
    """
    Clean the build artifacts by removing the build artifacts
    directory.
    """

    name = 'clean'
    helpmsg = (
        'Clean build artifacts, keep sstate cache and downloads.'
    )

    @classmethod
    def setup_parser(cls, parser):
        parser.add_argument('--dry-run',
                            action='store_true',
                            default=False,
                            help='Do not remove anything, just print what '
                                 'would be removed')
        parser.add_argument('--isar',
                            action='store_true',
                            default=False,
                            help='Use ISAR build directory layout')
        parser.add_argument('config',
                            help='Config file(s), separated by colon. Using '
                                 '.config.yaml in KAS_WORK_DIR if existing '
                                 'and none is specified.',
                            nargs='?')

    def run(self, args):
        ctx = create_global_context(args)
        build_system = None
        if args.config or (Path(ctx.kas_work_dir) / CONFIG_YAML_FILE).exists():
            ctx.config = Config(ctx, args.config)
            # to read the config, we need all repos (but no build env),
            macro = Macro()
            macro.run(ctx, skip=['repos_apply_patches', 'write_bb_config',
                                 'setup_environ'])
            build_system = ctx.config.get_build_system()
        if args.isar:
            build_system = 'isar'

        logging.debug('Run clean in "%s" mode' % (build_system or 'default'))
        if args.dry_run:
            logging.warning('Dry run, not removing anything')
        tmpdirs = Path(ctx.build_dir).glob('tmp*')
        for tmpdir in tmpdirs:
            logging.info(f'Removing {tmpdir}')
            if args.dry_run:
                continue
            if build_system == 'isar':
                clean_args = [
                    'sudo', '--prompt', '[sudo] enter password for %U '
                    f'to clean ISAR artifacts in {tmpdir}',
                    'rm', '-rf', str(tmpdir)]
                subprocess.check_call(clean_args)
            else:
                shutil.rmtree(tmpdir)

    @staticmethod
    def clear_dir_content(directory):
        """
        Clear the contents of a directory without removing the dir itself.
        """
        for item in directory.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()


class CleanSstate(Clean):
    """
    Removes the build artifacts and the empties the sstate cache.
    """

    name = 'cleansstate'
    helpmsg = (
        'Clean build artifacts and sstate cache.'
    )

    def run(self, args):
        super().run(args)
        ctx = get_context()
        sstate_dir = Path(os.environ.get('SSTATE_DIR',
                                         Path(ctx.build_dir) / 'sstate-cache'))
        if sstate_dir.exists():
            logging.info(f'Removing {sstate_dir}/*')
            if not args.dry_run:
                self.clear_dir_content(sstate_dir)


class CleanAll(CleanSstate):
    """
    Removes the build artifacts, empties the sstate cache and the downloads.
    """

    name = 'cleanall'
    helpmsg = (
        'Clean build artifacts, sstate-cache and downloads.'
    )

    def run(self, args):
        super().run(args)
        ctx = get_context()
        downloads_dir = Path(ctx.build_dir) / 'downloads'
        if downloads_dir.exists():
            logging.info(f'Removing {downloads_dir}/*')
            if not args.dry_run:
                self.clear_dir_content(downloads_dir)


__KAS_PLUGINS__ = [Clean, CleanSstate, CleanAll]
