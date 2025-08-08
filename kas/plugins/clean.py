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
from kas.includehandler import ConfigFile
from kas.libcmds import Macro
from kas.kasusererror import KasUserError
from kas import plugins


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
    config_files = None

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
        default_conf_file = Path(ctx.kas_work_dir) / CONFIG_YAML_FILE
        build_system = None
        if args.config:
            self.config_files = args.config
        elif default_conf_file.exists():
            self.config_files = str(default_conf_file)
        if self.config_files:
            # By definition, build_system key must be present in the first
            # config file to take effect.
            cf = ConfigFile.load(self.config_files.split(':')[0], False, False)
            build_system = cf.config.get('build_system')
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


class Purge(CleanAll):
    """
    Clears the contents of the build directory, sstate-cache, downloads and
    the repos managed by kas (including referenced repos in
    ``KAS_REPO_REF_DIR``, if set). In ``KAS_WORK_DIR`` it will remove the
    default configuration file and the ``KAS_BUILD_DIR`` (if present).
    To preserve the reference repositories, run with ``--preserve-repo-refs``.
    This command requires a configuration file to locate the managed repos.

    .. note::
        Before purging, kas needs to checkout and resolve all repos to locate
        the repos managed by kas.
    """

    name = 'purge'
    helpmsg = (
        'Purge all data managed by kas, including managed repos.'
    )

    @classmethod
    def setup_parser(cls, parser):
        super().setup_parser(parser)
        parser.add_argument('--preserve-repo-refs',
                            action='store_true',
                            default=False,
                            help='Do not remove the reference repositories')

    def run(self, args):
        super().run(args)
        ctx = get_context()

        if not self.config_files:
            raise KasUserError('Purge requires a config file to locate '
                               'managed repos.')

        ctx.config = Config(ctx, self.config_files)
        # to read the config, we need all repos (but no build env),
        macro = Macro()
        macro.run(ctx, skip=['repos_apply_patches', 'write_bb_config',
                             'setup_environ'])

        for r in ctx.config.get_repos():
            if r.operations_disabled:
                logging.debug(f'Skipping {r.name} as not managed by kas')
                continue
            logging.info(f'Removing {r.path}')
            if not args.dry_run:
                shutil.rmtree(r.path)
            if ctx.kas_repo_ref_dir and not args.preserve_repo_refs:
                ref_repo = Path(ctx.kas_repo_ref_dir) / r.qualified_name
                if ref_repo.exists():
                    logging.info(f'Removing {ref_repo}')
                    if not args.dry_run:
                        shutil.rmtree(ref_repo)

        build_dir = Path(ctx.build_dir)
        logging.info(f'Removing {build_dir}/*')
        if not args.dry_run:
            self.clear_dir_content(build_dir)

        work_dir = Path(ctx.kas_work_dir)
        default_config = work_dir / CONFIG_YAML_FILE
        if default_config.exists():
            logging.info(f'Removing {default_config}')
            if not args.dry_run:
                default_config.unlink()

        clean_paths = list(ctx.managed_paths)
        # Plugins can register additional paths by providing get_managed_paths.
        # These paths must be relative to the work_dir.
        for plugin in plugins.all():
            if hasattr(plugin, 'get_managed_paths'):
                ppaths = plugin.get_managed_paths()
                clean_paths.extend([work_dir / p for p in ppaths])

        for path in [Path(p) for p in clean_paths if Path(p).exists()]:
            logging.info(f'Removing {path}')
            if not args.dry_run:
                if path.is_file() or path.is_symlink():
                    path.unlink()
                else:
                    shutil.rmtree(path)


__KAS_PLUGINS__ = [Clean, CleanSstate, CleanAll, Purge]
