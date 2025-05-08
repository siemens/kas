# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2025
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

    .. note ::
       * all referenced repositories are checked out to resolve cross-repo
         configs
       * all branches are resolved before patches are applied

    **Updating lockfiles**

    When updating lockfiles, kas attempts to update the repository revisions
    in the lockfile that defines the revision. If a repository is exclusively
    locked in an external lockfile, this lock is not updated (we cannot modify
    an external repository). However, if the revision is also defined in a
    local lockfile, it is updated in the local lockfile.

    The algorithm for determining where to pin the revision of a repository
    is as follows:

    #. Find all repositories that have a floating ref (i.e. no commit). Assign
       to `to-lock` list
    #. Iterate over all lockfiles (in include order)

       #. for each repository, check if it is locked in the current file

          #. if lock is up to date, remove from `to-lock` list
          #. else if lockfile is internal, update lockfile, remove from
             `to-lock` list
          #. else (repo is locked in external lockfile): mark repo external

    #. Remove all repos with `external` marks from `to-lock` list
    #. Add all remaining repos in `to-lock` list to topmost lockfile,
       create if needed

    **Examples**

    The lockfile is created as ``kas-project.lock.yml``.
    Call again to regenerate lockfile::

        kas lock --update kas-project.yml

    The generated lockfile will automatically be used to pin the revisions::

        kas build kas-project.yml

    Note, that the lockfiles should be checked-in into the VCS.
"""

import logging
import os
from dataclasses import dataclass
from kas.context import get_context
from kas.includehandler import ConfigFile
from kas.plugins.checkout import Checkout
from kas.plugins.dump import Dump, IoTarget, LOCKFILE_VERSION_MIN
from kas.repos import Repo

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

    @dataclass
    class RepoInfo():
        repo: Repo
        ext_lock: bool

    @classmethod
    def setup_parser(cls, parser):
        super().setup_parser(parser)
        Dump.setup_parser_format_args(parser)

    def _update_lockfile(self, lockfile, repos_to_lock, update_only, args):
        """
        Update all locks in the given lockfile.
        If update_only, no new locks are added.
        """
        output = IoTarget(target=lockfile, managed=True)
        lockfile_config = lockfile.config
        changed = False

        if 'overrides' not in lockfile_config:
            lockfile_config['overrides'] = {'repos': {}}
        if 'repos' not in lockfile_config['overrides']:
            lockfile_config['overrides']['repos'] = {}
        lock_header_vers = lockfile_config['header']['version']
        if lock_header_vers < LOCKFILE_VERSION_MIN:
            logging.warning('Lockfile uses too-old header version (%s). '
                            'Updating to version %d',
                            lock_header_vers, LOCKFILE_VERSION_MIN)
            lockfile_config['header']['version'] = LOCKFILE_VERSION_MIN

        for k, v in lockfile_config['overrides']['repos'].items():
            ri = repos_to_lock.get(k)
            if not ri:
                continue

            r = ri.repo
            if v['commit'] == r.revision:
                logging.info('Lock of %s is up-to-date: %s',
                             r.name, r.revision)
            elif not lockfile.is_external:
                logging.info('Updating lock of %s: %s -> %s',
                             r.name, v['commit'], r.revision)
                v['commit'] = r.revision
                changed = True
            else:
                logging.warning(
                    'Repo %s is locked in remote lockfile %s. '
                    'Not updating.', r.name, lockfile.filename)
                ri.ext_lock = True
                continue
            del repos_to_lock[k]

        if not update_only:
            for k, ri in repos_to_lock.items():
                r = ri.repo
                logging.info('Adding lock of %s: %s', r.name, r.revision)
                lockfile_config['overrides']['repos'][k] = \
                    {'commit': r.revision}
                changed = True

        if not changed:
            return repos_to_lock

        logging.info('Updating lockfile %s',
                     os.path.relpath(lockfile.filename, os.getcwd()))
        output = IoTarget(target=lockfile.filename, managed=True)
        format = "json" if lockfile.filename.suffix == '.json' else "yaml"
        Dump.dump_config(lockfile_config, output, format,
                         args.indent, args.sort)
        return repos_to_lock

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
        repos_cfg = ctx.config.repo_dict.items()
        # when locking, only consider floating repos managed by kas
        # Important: process repos in the order they are defined in the
        # config file to update lockfile with highest precedence.
        repos_to_lock = dict([(k, self.RepoInfo(r, False)) for k, r
                              in _filter_enabled(repos_cfg)
                              if not r.commit])
        if not repos_to_lock:
            logging.info('No floating repos found. Nothing to lock.')
            return

        # first update all locks we have without creating new ones
        lockfiles = ctx.config.get_lockfiles()
        for lock in lockfiles:
            repos_to_lock = self._update_lockfile(lock, repos_to_lock,
                                                  True, args)

        # remove repos that are externally locked
        repos_to_lock = {k: v for k, v in repos_to_lock.items()
                         if not v.ext_lock}

        # then add new locks for the remaining repos to the default lockfile
        if repos_to_lock:
            repo_to_lock_names = [r.repo.name for r in repos_to_lock.values()]
            logging.warning('The following repos are not covered by any '
                            'lockfile. Adding to top lockfile: %s',
                            ', '.join(repo_to_lock_names))
            lockpath = ctx.config.handler.get_lock_filename()
            if lockfiles and lockfiles[0].filename == lockpath:
                lock = lockfiles[0]
            else:
                lock = ConfigFile(lockpath, is_external=False,
                                  is_lockfile=True)
                lock.config['header'] = {'version': LOCKFILE_VERSION_MIN}
            self._update_lockfile(lock, repos_to_lock, False, args)


__KAS_PLUGINS__ = [Lock]
