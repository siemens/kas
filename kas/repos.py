# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2019
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
    This module contains the Repo class.
"""

import re
import os
import sys
import logging
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from .context import get_context
from .libkas import run_cmd_async, run_cmd
from .kasusererror import KasUserError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class UnsupportedRepoTypeError(KasUserError, NotImplementedError):
    """
    The requested repo type is unsupported / not implemented
    """
    pass


class RepoRefError(KasUserError):
    """
    The requested repo reference is invalid, missing or could not be found
    """
    pass


class PatchFileNotFound(KasUserError, FileNotFoundError):
    """
    The requested patch file was not found
    """
    pass


class PatchMappingError(KasUserError):
    """
    The requested patch can not be related to a repo
    """
    pass


class PatchApplyError(KasUserError):
    """
    The provided patch file could not be applied
    """


class Repo:
    """
        Represents a repository in the kas configuration.
    """

    def __init__(self, name, url, path, commit, branch, refspec, layers,
                 patches, disable_operations):
        self.name = name
        self.url = url
        self.path = path
        self.commit = commit
        self.branch = branch
        self.refspec = refspec
        self._layers = layers
        self._patches = patches
        self.operations_disabled = disable_operations

    def __getattr__(self, item):
        if item == 'layers':
            return [os.path.join(self.path, layer).rstrip(os.sep + '.')
                    for layer in self._layers]
        elif item == 'qualified_name':
            url = urlparse(self.url)
            return ('{url.netloc}{url.path}'
                    .format(url=url)
                    .replace('@', '.')
                    .replace(':', '.')
                    .replace('/', '.')
                    .replace('*', '.'))
        elif item == 'effective_url':
            mirrors = os.environ.get('KAS_PREMIRRORS', '')
            for mirror in mirrors.split('\n'):
                try:
                    expr, subst = mirror.split()
                    if re.match(expr, self.url):
                        return re.sub(expr, subst, self.url)
                except ValueError:
                    continue
            return self.url
        elif item == 'revision':
            if self.commit:
                return self.commit
            branch = self.branch or self.refspec
            if not branch:
                return None
            (_, output) = run_cmd(self.resolve_branch_cmd(),
                                  cwd=self.path, fail=False)
            if output:
                return output.strip()
            return branch

        # Default behaviour
        raise AttributeError

    def __str__(self):
        if self.commit and self.branch:
            return '%s:%s(%s) %s %s' % (self.url, self.commit, self.branch,
                                        self.path, self._layers)
        return '%s:%s %s %s' % (self.url,
                                self.commit or self.branch or self.refspec,
                                self.path, self._layers)

    __legacy_refspec_warned__ = []

    @staticmethod
    def factory(name, repo_config, repo_defaults, repo_fallback_path,
                repo_overrides={}):
        """
            Returns a Repo instance depending on params.
        """
        layers_dict = repo_config.get('layers', {'': None})
        layers = list(filter(lambda x, laydict=layers_dict:
                             str(laydict[x]).lower() not in
                             ['disabled', 'excluded', 'n', 'no', '0', 'false'],
                             layers_dict))
        default_patch_repo = repo_defaults.get('patches', {}).get('repo', None)
        patches_dict = repo_config.get('patches', {})
        patches = []
        for p in sorted(patches_dict):
            if not patches_dict[p]:
                continue
            this_patch = {
                'id': p,
                'repo': patches_dict[p].get('repo', default_patch_repo),
                'path': patches_dict[p]['path'],
            }
            if this_patch['repo'] is None:
                raise PatchMappingError(
                    'No repo specified for patch entry "{}" and no '
                    'default repo specified.'.format(p))

            patches.append(this_patch)

        url = repo_config.get('url', None)
        name = repo_config.get('name', name)
        typ = repo_config.get('type', 'git')
        commit = repo_config.get('commit', None)
        branch = repo_config.get('branch', repo_defaults.get('branch', None))
        refspec = repo_config.get('refspec',
                                  repo_defaults.get('refspec', None))
        if commit is None and branch is None and refspec is None \
                and url is not None:
            raise RepoRefError('No commit or branch specified for repository '
                               '"{}". This is only allowed for local '
                               'repositories.'.format(name))
        if refspec is None:
            commit = repo_overrides.get('commit', commit)
        else:
            if name not in Repo.__legacy_refspec_warned__:
                logging.warning('Using deprecated refspec for repository '
                                '"%s". You should migrate to commit/branch.',
                                name)
                Repo.__legacy_refspec_warned__.append(name)
            if commit is not None or branch is not None:
                raise RepoRefError('Unsupported mixture of legacy refspec '
                                   'and commit/branch for repository "{}"'
                                   .format(name))
            refspec = repo_overrides.get('commit', refspec)
        path = repo_config.get('path', None)
        disable_operations = False

        if path is None:
            if url is None:
                path = Repo.get_root_path(repo_fallback_path)
                logging.info('Using %s as root for repository %s', path,
                             name)
            else:
                path = os.path.join(get_context().kas_work_dir, name)
        elif not os.path.isabs(path):
            # Relative pathes are assumed to start from work_dir
            path = os.path.join(get_context().kas_work_dir, path)

        if url is None:
            # No version control operation on repository
            url = path
            disable_operations = True

        if typ == 'git':
            return GitRepo(name, url, path, commit, branch, refspec, layers,
                           patches, disable_operations)
        if typ == 'hg':
            return MercurialRepo(name, url, path, commit, branch, refspec,
                                 layers, patches, disable_operations)
        raise UnsupportedRepoTypeError('Repo type "%s" not supported.' % typ)

    @staticmethod
    def get_root_path(path, fallback=True):
        """
            Checks if path is under version control and returns its root path.
        """
        (ret, output) = run_cmd(['git', 'rev-parse', '--show-toplevel'],
                                cwd=path, fail=False, liveupdate=False)
        if ret == 0:
            return output.strip()

        (ret, output) = run_cmd(['hg', 'root'],
                                cwd=path, fail=False, liveupdate=False)
        if ret == 0:
            return output.strip()

        return path if fallback else None


class RepoImpl(Repo):
    """
        Provides a generic implementation for a Repo.
    """

    async def fetch_async(self):
        """
            Starts asynchronous repository fetch.
        """

        if self.operations_disabled:
            return 0

        refdir = get_context().kas_repo_ref_dir
        sdir = os.path.join(refdir, self.qualified_name) if refdir else None

        # fetch to refdir
        if refdir and not os.path.exists(sdir):
            os.makedirs(refdir, exist_ok=True)
            with TemporaryDirectory(prefix=self.qualified_name + '.',
                                    dir=refdir) as tmpdir:
                (retc, _) = await run_cmd_async(
                    self.clone_cmd(tmpdir, createref=True),
                    cwd=get_context().kas_work_dir)

                logging.debug('Created repo ref for %s', self.qualified_name)
                try:
                    os.rename(tmpdir, sdir)
                    if sys.version_info < (3, 8):
                        # recreate dir so cleanup handler can delete it
                        os.makedirs(tmpdir, exist_ok=True)
                except OSError:
                    logging.debug('repo %s already cloned by other instance',
                                  self.qualified_name)

        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            (retc, _) = await run_cmd_async(
                self.clone_cmd(sdir, createref=False),
                cwd=get_context().kas_work_dir)

            logging.info('Repository %s cloned', self.name)

        # Make sure the remote origin is set to the value
        # in the kas file to avoid surprises
        try:
            (retc, output) = await run_cmd_async(
                self.set_remote_url_cmd(),
                cwd=self.path,
                liveupdate=False)
        except NotImplementedError:
            logging.warning('Repo implementation does not support changing '
                            'the remote url.')

        # take what came out of clone and stick to that forever
        if self.commit is None and self.branch is None \
           and self.refspec is None:
            return 0

        if not get_context().update:
            # Do commit/branch/refspec exist in the current repository?
            (retc, output) = await run_cmd_async(self.contains_refspec_cmd(),
                                                 cwd=self.path,
                                                 fail=False,
                                                 liveupdate=False)
            if retc == 0:
                logging.info('Repository %s already contains %s as %s',
                             self.name,
                             self.commit or self.branch or self.refspec,
                             output.strip())
                return retc

        # Try to fetch if commit/branch/refspec is missing or if --update
        # argument was passed
        (retc, output) = await run_cmd_async(self.fetch_cmd(),
                                             cwd=self.path,
                                             fail=False)
        if retc:
            logging.warning('Could not update repository %s: %s',
                            self.name, output)
        else:
            logging.info('Repository %s updated', self.name)
        return 0

    def checkout(self):
        """
            Checks out the correct revision of the repo.
        """
        if self.operations_disabled \
            or (self.commit is None and self.branch is None
                and self.refspec is None):
            return

        if not get_context().force_checkout:
            # Check if repos is dirty
            (_, output) = run_cmd(self.is_dirty_cmd(),
                                  cwd=self.path,
                                  fail=False)
            if output:
                logging.warning('Repo %s is dirty - no checkout', self.name)
                return

        if self.commit:
            desired_ref = self.commit
            is_branch = False
        else:
            (_, output) = run_cmd(self.resolve_branch_cmd(),
                                  cwd=self.path, fail=False)
            if output:
                desired_ref = output.strip()
                is_branch = True
            elif self.branch:
                raise RepoRefError(
                    'Branch "{}" cannot be found in repository {}'
                    .format(self.branch, self.name))
            else:
                desired_ref = self.refspec
                is_branch = False

        run_cmd(self.checkout_cmd(desired_ref, is_branch), cwd=self.path)

    async def apply_patches_async(self):
        """
            Applies patches to a repository asynchronously.
        """
        if self.operations_disabled or not self._patches:
            return 0

        (retc, _) = await run_cmd_async(self.prepare_patches_cmd(),
                                        cwd=self.path)

        my_patches = []

        for patch in self._patches:
            other_repo = get_context().config.repo_dict.get(patch['repo'],
                                                            None)

            if not other_repo:
                raise PatchMappingError(
                    'Could not find referenced repo. '
                    '(missing repo: {}, repo: {}, patch entry: {})'
                    .format(patch['repo'], self.name, patch['id']))

            path = os.path.join(other_repo.path, patch['path'])
            cmd = []

            if os.path.isfile(path):
                my_patches.append((path, patch['id']))
            elif os.path.isdir(path) \
                    and os.path.isfile(os.path.join(path, 'series')):
                with open(os.path.join(path, 'series')) as f:
                    for line in f:
                        if line.startswith('#'):
                            continue
                        p = os.path.join(path, line.split(' #')[0].rstrip())
                        if os.path.isfile(p):
                            my_patches.append((p, patch['id']))
                        else:
                            raise PatchFileNotFound(p)
            else:
                raise PatchFileNotFound(
                    'Could not find patch. '
                    '(patch path: {}, repo: {}, patch entry: {})'
                    .format(path, self.name, patch['id']))

        for (path, patch_id) in my_patches:
            cmd = self.apply_patches_file_cmd(path)
            (retc, output) = await run_cmd_async(
                cmd, cwd=self.path, fail=False)
            if retc:
                raise PatchApplyError(
                    'Could not apply patch. Please fix repos and '
                    'patches. (patch path: {}, repo: {}, patch '
                    'entry: {}, vcs output: {})'
                    .format(path, self.name, patch_id, output))

            logging.info('Patch applied. '
                         '(patch path: %s, repo: %s, patch entry: %s)',
                         path, self.name, patch_id)

            cmd = self.add_cmd()
            (retc, output) = await run_cmd_async(
                cmd, cwd=self.path, fail=False)
            if retc:
                raise PatchApplyError(
                    'Could not add patched files. repo: {}, vcs output: {})'
                    .format(self.name, output))

            cmd = self.commit_cmd()
            (retc, output) = await run_cmd_async(
                cmd, cwd=self.path, fail=False)
            if retc:
                raise PatchApplyError(
                    'Could not commit patch changes. repo: {}, vcs output: {})'
                    .format(self.name, output))

        return 0


class GitRepo(RepoImpl):
    """
        Provides the git functionality for a Repo.
    """

    def remove_ref_prefix(self, branch):
        ref_prefix = 'refs/'
        return branch[branch.startswith(ref_prefix) and len(ref_prefix):]

    def add_cmd(self):
        return ['git', 'add', '-A']

    def clone_cmd(self, srcdir, createref):
        cmd = ['git', 'clone', '-q']
        if createref:
            cmd.extend([self.effective_url, '--bare', srcdir])
        elif srcdir:
            cmd.extend([srcdir, '--reference', srcdir, self.path])
        else:
            cmd.extend([self.effective_url, self.path])
        return cmd

    def commit_cmd(self):
        return ['git', 'commit', '-a', '--author', 'kas <kas@example.com>',
                '-m', 'msg']

    def contains_refspec_cmd(self):
        branch = self.branch or self.refspec
        if branch and branch.startswith('refs/'):
            branch = 'remotes/origin/' + self.remove_ref_prefix(branch)
        return ['git', 'cat-file', '-t', self.commit or branch]

    def fetch_cmd(self):
        cmd = ['git', 'fetch', '-q']
        branch = self.branch or self.refspec
        if branch and branch.startswith('refs/'):
            cmd.extend(['origin',
                        '+' + branch
                        + ':refs/remotes/origin/'
                        + self.remove_ref_prefix(branch)])

        return cmd

    def is_dirty_cmd(self):
        return ['git', 'status', '-s']

    def resolve_branch_cmd(self):
        return ['git', 'rev-parse', '--verify', '-q',
                'origin/{branch}'.
                format(branch=self.remove_ref_prefix(
                    self.branch or self.refspec))]

    def checkout_cmd(self, desired_ref, is_branch):
        cmd = ['git', 'checkout', '-q', self.remove_ref_prefix(desired_ref)]
        if is_branch:
            branch = self.remove_ref_prefix(self.branch or self.refspec)
            branch = branch[branch.startswith('heads/') and len('heads/'):]
            cmd.extend(['-B', branch])
        if get_context().force_checkout:
            cmd.append('--force')
        return cmd

    def prepare_patches_cmd(self):
        branch = self.branch or self.refspec
        return ['git', 'checkout', '-q', '-B',
                'patched-{refspec}'.
                format(refspec=self.commit or self.remove_ref_prefix(branch))]

    def apply_patches_file_cmd(self, path):
        return ['git', 'apply', '--whitespace=nowarn', path]

    def set_remote_url_cmd(self):
        return ['git', 'remote', 'set-url', 'origin', self.effective_url]


class MercurialRepo(RepoImpl):
    """
        Provides the hg functionality for a Repo.
    """

    def add_cmd(self):
        return ['hg', 'add']

    def clone_cmd(self, srcdir, createref):
        # Mercurial does not support repo references (object caches)
        if createref:
            return ['true']
        return ['hg', 'clone', self.effective_url, self.path]

    def commit_cmd(self):
        return ['hg', 'commit', '--user', 'kas <kas@example.com>', '-m', 'msg']

    def contains_refspec_cmd(self):
        return ['hg', 'log', '-r', self.commit or self.branch or self.refspec]

    def fetch_cmd(self):
        return ['hg', 'pull']

    def is_dirty_cmd(self):
        return ['hg', 'diff']

    def resolve_branch_cmd(self):
        return ['hg', 'identify', '--id', '-r', self.branch or self.refspec,
                'default']

    def checkout_cmd(self, desired_ref, is_branch):
        cmd = ['hg', 'checkout', desired_ref]
        if get_context().force_checkout:
            cmd.append('--clean')
        return cmd

    def prepare_patches_cmd(self):
        refspec = self.commit or self.branch or self.refspec
        return ['hg', 'branch', '-f',
                'patched-{refspec}'.format(refspec=refspec)]

    def apply_patches_file_cmd(self, path):
        return ['hg', 'import', '--no-commit', path]

    def set_remote_url_cmd(self):
        raise NotImplementedError()
