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
import linecache
import logging
import shutil
from datetime import datetime
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from .context import get_context
from .libkas import run_cmd_async, run_cmd
from .kasusererror import KasUserError
from functools import cached_property
from git import Repo as GitPythonRepo

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
    def __init__(self, msg, cmd=None, out=None, err=None):
        if cmd:
            msg += '\nvcs command: ' + ' '.join(cmd)
        if out and out.strip():
            msg += f'\nvcs output:\n{out.strip()}'
        if err and err.strip():
            msg += f'\nvcs error:\n{err.strip()}'
        super().__init__(msg)


class Repo:
    """
        Represents a repository in the kas configuration.
    """

    def __init__(self, name, url, path, commit, tag, branch, refspec, layers,
                 patches, signers, disable_operations):
        self.name = name
        self.url = url
        self.path = path
        self.commit = commit
        self.tag = tag
        self.branch = branch
        self.refspec = refspec
        self._layers = layers
        self._patches = patches
        self.allowed_signers = signers
        self.operations_disabled = disable_operations

        if not self.url:
            self.resolve_local()

    @property
    def layers(self):
        return [os.path.join(self.path, layer).rstrip(os.sep + '.')
                for layer in self._layers]

    @property
    def qualified_name(self):
        url = urlparse(self.url)
        return (f'{url.netloc}{url.path}'
                .replace('@', '.')
                .replace(':', '.')
                .replace('/', '.')
                .replace('*', '.'))

    @property
    def effective_url(self):
        mirrors = os.environ.get('KAS_PREMIRRORS', '')
        for mirror in mirrors.split('\n'):
            try:
                expr, subst = mirror.split()
                if re.match(expr, self.url):
                    return re.sub(expr, subst, self.url)
            except ValueError:
                continue
        return self.url

    @cached_property
    def revision(self):
        if self.commit:
            (_, output) = run_cmd(self.get_commit_cmd(),
                                  cwd=self.path, fail=False)
            if output:
                return output.strip()
            return self.commit
        if self.tag:
            (_, output) = run_cmd(self.resolve_tag_cmd(),
                                  cwd=self.path, fail=False)
            if output:
                return output.strip()
            return self.tag
        branch = self.branch or self.refspec
        if branch:
            (_, output) = run_cmd(self.resolve_branch_cmd(),
                                  cwd=self.path, fail=False)
            if output:
                return output.strip()
            return branch
        return None

    @cached_property
    def dirty(self):
        if not self.url:
            return True
        (_, output) = run_cmd(self.is_dirty_cmd(),
                              cwd=self.path, fail=False)
        return bool(output)

    @cached_property
    def signers_type(self):
        if self.allowed_signers is None:
            return 'gpg'
        signers = get_context().config.get_signers_config()
        try:
            ktypes = [signers[k].get('type', 'gpg')
                      for k in self.allowed_signers]
        except KeyError as e:
            raise KasUserError(f'Repository {self.name}: '
                               f'Allowed signer "{e}" not found in config')
        if len(set(ktypes)) > 1:
            raise KasUserError(f'Repository {self.name}: '
                               'Mixed signer types are not supported')
        return ktypes[0]

    @property
    def keyhandler(self):
        if not self.signed:
            return None
        return get_context().keyhandler[self.signers_type]

    def check_signature(self):
        self.keyhandler.prepare_validation(self)
        (ret, _, err) = run_cmd(self.is_signed_cmd(),
                                cwd=self.path, fail=False, capture_stderr=True)
        logging.debug('Signature verification output (%d):\n%s', ret, err)
        if ret != 0:
            return (False, None)
        return self.keyhandler.validate_allowed_signer(self, err)

    @cached_property
    def signed(self):
        return self.allowed_signers is not None

    @staticmethod
    def get_type():
        """
            Repo type as defined in spdx-spec/v2.3/package-information
        """
        raise NotImplementedError("Repo type not implemented")

    def contains_path(self, path):
        (ret, _) = run_cmd(self.contains_path_cmd(str(path)),
                           cwd=self.path, fail=False)
        return ret == 0

    def __str__(self):
        if self.commit and (self.tag or self.branch):
            refspec = f'{self.commit}({self.tag or self.branch})'
        else:
            refspec = self.commit or self.tag or self.branch or self.refspec

        return f'{self.url}:{refspec} ' \
               f'{self.path} {self._layers}'

    __legacy_refspec_warned__ = []
    __no_commit_tag_warned__ = []

    @staticmethod
    def factory(name, repo_config, repo_defaults, repo_fallback_path,
                repo_overrides={}):
        """
            Returns a Repo instance depending on parameters.
            This factory function is referential transparent.
        """
        layers_dict = repo_config.get('layers', {'': None})
        # only bool(false) will be a valid value to disable a layer
        for lname, prop in layers_dict.items():
            if not (prop is None or prop == "disabled"):
                logging.warning('Use of deprecated value "%s" for repo '
                                '"%s", layer "%s". Replace with "disabled".',
                                prop, name, lname)

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
                    f'No repo specified for patch entry "{p}" and no '
                    'default repo specified.')

            patches.append(this_patch)

        url = repo_config.get('url', None)
        name = repo_config.get('name', name)
        repo_type = repo_config.get('type', 'git')
        commit = repo_config.get('commit', None)
        tag = repo_config.get('tag', repo_defaults.get('tag', None))
        branch = repo_config.get('branch', repo_defaults.get('branch', None))
        refspec = repo_config.get('refspec',
                                  repo_defaults.get('refspec', None))
        if commit is None and tag is None and branch is None \
                and refspec is None and url is not None:
            raise RepoRefError('No commit, tag or branch specified for '
                               f'repository "{name}". This is only allowed '
                               'for local repositories.')
        if refspec is None:
            commit = repo_overrides.get('commit', commit)
            if commit and get_context().update:
                logging.warning(f'Update of "{name}" requested, but repo is '
                                'pinned to a fixed commit. Not updating.')
        else:
            if name not in Repo.__legacy_refspec_warned__:
                logging.warning('Using deprecated refspec for repository "%s".'
                                ' You should migrate to commit/tag/branch.',
                                name)
                Repo.__legacy_refspec_warned__.append(name)
            if commit is not None or tag is not None or branch is not None:
                raise RepoRefError(
                    'Unsupported mixture of legacy refspec and '
                    f'commit/tag/branch for repository "{name}"')
            refspec = repo_overrides.get('commit', refspec)
        if tag and not commit:
            if name not in Repo.__no_commit_tag_warned__:
                logging.warning('Using tag without commit for repository '
                                '"%s" is unsafe as tags are mutable.', name)
                Repo.__no_commit_tag_warned__.append(name)
        path = repo_config.get('path', None)
        signed = repo_config.get('signed', False)
        signers = repo_config.get('allowed_signers', None) if signed else None
        if signed and not signers:
            raise KasUserError(f'Repository "{name}" is signed but no allowed '
                               'signers specified.')
        disable_operations = False

        if path is None:
            if url is None:
                path = Repo.get_root_path(repo_fallback_path)
                logging.info('Using %s as root for repository %s', path, name)
            else:
                path = os.path.join(get_context().kas_work_dir, name)
        elif not os.path.isabs(path):
            # Relative pathes are assumed to start from work_dir
            path = os.path.join(get_context().kas_work_dir, path)

        if url is None:
            # No version control operation on repository
            disable_operations = True

        if repo_type == 'git':
            if commit and not re.match(r'^[0-9a-f]{40}|[0-9a-f]{64}$', commit):
                logging.warning(
                    f'{commit} is not a full-length hash for repo '
                    f'"{name}". This will be an error in future versions.')
            return GitRepo(name, url, path, commit, tag, branch, refspec,
                           layers, patches, signers, disable_operations)
        if repo_type == 'hg':
            if not shutil.which('hg'):
                raise UnsupportedRepoTypeError(
                    'hg is required for Mercurial repositories')
            return MercurialRepo(name, url, path, commit, tag, branch, refspec,
                                 layers, patches, signers, disable_operations)
        raise UnsupportedRepoTypeError(f'Repo type "{repo_type}" '
                                       'not supported.')

    @staticmethod
    def get_root_path(path, fallback=True):
        """
            Checks if path is under version control and returns its root path.
            If the repo is a submodule, the root path of the super-repository
            is returned.
        """
        git_cmd = ['git', 'rev-parse', '--show-toplevel',
                   '--show-superproject-working-tree']
        (ret, output) = run_cmd(git_cmd, cwd=path, fail=False)
        if ret == 0:
            return sorted(output.strip().split('\n'))[0]

        (ret, output) = run_cmd(['hg', 'root'],
                                cwd=path, fail=False)
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
                except OSError:
                    logging.debug('repo %s already cloned by other instance',
                                  self.qualified_name)

        if not os.path.exists(self.path):
            logging.info('Cloning repository %s', self.name)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            (retc, _) = await run_cmd_async(
                self.clone_cmd(sdir, createref=False),
                cwd=get_context().kas_work_dir)

        # Make sure the remote origin is set to the value
        # in the kas file to avoid surprises
        try:
            (retc, output) = await run_cmd_async(
                self.set_remote_url_cmd(),
                cwd=self.path)
        except NotImplementedError:
            logging.warning('Repo implementation does not support changing '
                            'the remote url.')

        # take what came out of clone and stick to that forever
        if self.commit is None and self.tag is None and self.branch is None \
           and self.refspec is None:
            return 0

        if not get_context().update:
            # Do commit/tag/branch/refspec exist in the current repository?
            (retc, output) = await run_cmd_async(self.contains_refspec_cmd(),
                                                 cwd=self.path,
                                                 fail=False)
            if retc == 0:
                logging.info('Repository %s already contains %s as %s',
                             self.name,
                             self.commit or self.tag or self.branch
                             or self.refspec,
                             output.strip())
                # if branch is specified, check if it contains the commit
                # also in our local clone
                depth = get_context().repo_clone_depth
                if self.branch and self.commit and not depth:
                    (_, output) = await run_cmd_async(
                        self.branch_contains_ref(), cwd=self.path, fail=False)
                    if output.strip():
                        return retc
                else:
                    return retc

        # Try to fetch if commit/tag/branch/refspec is missing or if --update
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
            or (self.commit is None and self.tag is None
                and self.branch is None and self.refspec is None):
            return

        if not get_context().force_checkout:
            # Check if repos is dirty
            if self.dirty:
                logging.warning('Repo %s is dirty - no checkout', self.name)
                return

        if self.tag and self.branch:
            raise RepoRefError(
                f'Both tag "{self.tag}" and branch "{self.branch}" '
                f'cannot be specified for repository "{self.name}"')

        if self.tag:
            (retc, output) = run_cmd(self.resolve_tag_cmd(),
                                     cwd=self.path,
                                     fail=False)
            if retc:
                raise RepoRefError(f'Tag "{self.tag}" cannot be found '
                                   f'in repository "{self.name}"')

            desired_ref = output.strip()
            if self.commit and desired_ref != self.commit:
                # Ensure provided commit and tag match
                raise RepoRefError(f'Provided tag "{self.tag}" '
                                   f'("{desired_ref}") does not match '
                                   f'provided commit "{self.commit}" in '
                                   f'repository "{self.name}", aborting!')
            is_branch = False
        elif self.branch:
            (retc, output) = run_cmd(self.resolve_branch_cmd(),
                                     cwd=self.path,
                                     fail=False)
            if retc:
                raise RepoRefError(
                    f'Branch "{self.branch}" cannot be found '
                    f'in repository "{self.name}"')
            # check if branch contains the requested commit.
            # skip check on shallow clones, as branch information is missing
            if self.commit and not get_context().repo_clone_depth:
                (_, output) = run_cmd(self.branch_contains_ref(),
                                      cwd=self.path,
                                      fail=False)
                if not output.strip():
                    raise RepoRefError(
                        f'Branch "{self.branch}" in '
                        f'repository "{self.name}" does not contain '
                        f'commit "{self.commit}"')

            desired_ref = self.commit or output.strip()
            is_branch = True
        elif self.commit:
            desired_ref = self.commit
            is_branch = False
        else:
            desired_ref = self.refspec
            is_branch = False

        run_cmd(self.checkout_cmd(desired_ref, is_branch), cwd=self.path)
        logging.info(f'Repository {self.name} checked out to {desired_ref}')

    async def apply_patches_async(self):
        """
            Applies patches to a repository asynchronously.
        """
        if self.operations_disabled or not self._patches:
            return 0

        if self.dirty:
            logging.warning(f'Repo {self.name} is dirty - no patching')
            return 0

        (retc, _) = await run_cmd_async(self.prepare_patches_cmd(),
                                        cwd=self.path)

        my_patches = []

        for patch in self._patches:
            other_repo = get_context().config.repo_dict.get(patch['repo'],
                                                            None)

            if not other_repo:
                raise PatchMappingError('Could not find referenced repo. '
                                        f'(missing repo: {patch["repo"]}, '
                                        f'repo: {self.name}, '
                                        f'patch entry: {patch["id"]})')

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
                    f'(patch path: {path}, repo: {self.name}, patch '
                    f'entry: {patch["id"]})')

        for (path, patch_id) in my_patches:
            cmd = self.apply_patches_file_cmd(path)
            (retc, out, err) = await run_cmd_async(
                cmd, cwd=self.path, fail=False, capture_stderr=True)
            if retc:
                raise PatchApplyError(
                    'Could not apply patch. Please fix repos and patches:\n'
                    f'patch path: {path}, repo: {self.name}, patch '
                    f'entry: {patch_id}', cmd, out, err)

            logging.info('Patch applied. '
                         '(patch path: %s, repo: %s, patch entry: %s)',
                         path, self.name, patch_id)

            cmd = self.add_cmd()
            (retc, out, err) = await run_cmd_async(
                cmd, cwd=self.path, fail=False, capture_stderr=True)
            if retc:
                raise PatchApplyError('Could not add patched files: repo: '
                                      f'{self.name}', cmd, out, err)

            timestamp = self.get_patch_timestamp(path)
            if not timestamp:
                dt = datetime.fromtimestamp(os.path.getmtime(path))
                timestamp = dt.astimezone().strftime(
                    "%a, %d %b %Y %H:%M:%S %z")

            env = get_context().environ.copy()
            msg = f'kas: {patch_id}\n\npatch {path} applied by kas'
            cmd = self.commit_cmd(env, 'kas <kas@example.com>', msg,
                                  timestamp)
            (retc, out, err) = await run_cmd_async(
                cmd, cwd=self.path, env=env, fail=False, capture_stderr=True)
            if retc:
                raise PatchApplyError('Could not commit patch changes. repo: '
                                      f'{self.name}', cmd, out, err)

        return 0

    def resolve_local(self):
        (retc, output) = run_cmd(self.get_remote_url_cmd(),
                                 cwd=self.path, fail=False)
        if retc == 0:
            self.url = output.strip()

        (retc, output) = run_cmd(self.get_commit_cmd(),
                                 cwd=self.path, fail=False)
        if retc == 0:
            self.commit = output.strip()
        if self.url and self.commit:
            logging.debug('Repository %s resolved to %s @ %s',
                          self.name, self.url, self.commit)


class GitRepo(RepoImpl):
    """
        Provides the git functionality for a Repo.
    """

    @staticmethod
    def get_type():
        return 'git'

    def remove_ref_prefix(self, ref):
        ref_prefix = 'refs/'
        return ref[ref.startswith(ref_prefix) and len(ref_prefix):]

    def add_cmd(self):
        return ['git', 'add', '-A']

    def clone_cmd(self, srcdir, createref):
        cmd = ['git', 'clone', '-q']

        depth = get_context().repo_clone_depth
        if depth:
            if self.refspec:
                logging.warning('Shallow cloning is not supported for legacy '
                                f'refspec on repository "{self.name}". '
                                'Performing full clone.')
            else:
                if createref:
                    # this is not a user-error, as the clone of the work repo
                    # can still be shallow.
                    logging.debug('Shallow cloning is not supported for '
                                  f'reference repository of "{self.name}". '
                                  'Performing full clone.')
                else:
                    cmd.extend(['--depth', str(depth)])
                if self.branch:
                    cmd.extend(['--branch',
                                self.remove_ref_prefix(self.branch)])

        if createref:
            cmd.extend([self.effective_url, '--bare', srcdir])
        elif srcdir:
            cmd.extend([srcdir, '--reference', srcdir, self.path])
        else:
            cmd.extend([self.effective_url, self.path])
        return cmd

    def commit_cmd(self, env, author, msg, date):
        env["GIT_COMMITTER_DATE"] = date
        return ['git', 'commit', '-a', '--author', author, '-m', msg,
                '--date', date]

    def contains_refspec_cmd(self):
        branch = self.branch or self.refspec
        if branch and branch.startswith('refs/'):
            branch = 'remotes/origin/' + self.remove_ref_prefix(branch)
        return ['git', 'cat-file', '-t', self.commit or self.tag or branch]

    def fetch_cmd(self):
        cmd = ['git', 'fetch', '-q']

        depth = 0 if self.refspec else get_context().repo_clone_depth
        if depth:
            cmd.extend(['--depth', str(depth)])

        if self.tag:
            cmd.extend(['origin', f'+{self.tag}:refs/tags/{self.tag}'])
            return cmd

        # only fetch this commit (branch information is lost)
        if depth and self.commit:
            cmd.extend(['origin', self.commit])
            return cmd

        branch = self.branch or self.refspec
        if branch and (branch.startswith('refs/') or depth):
            branch = self.remove_ref_prefix(branch)
            cmd.extend(['origin', f'+{branch}:refs/remotes/origin/{branch}'])

        return cmd

    def is_dirty_cmd(self):
        return ['git', 'diff', '--stat']

    def is_signed_cmd(self):
        if self.tag:
            return ['git', 'verify-tag', '--raw', self.tag]
        else:
            refspec = self.commit or self.revision
            return ['git', 'verify-commit', '--raw', refspec]

    def resolve_branch_cmd(self):
        refspec = self.remove_ref_prefix(self.branch or self.refspec)
        return ['git', 'rev-parse', '--verify', '-q', f'origin/{refspec}']

    def resolve_tag_cmd(self):
        return ['git', 'rev-list', '-n', '1', self.remove_ref_prefix(self.tag)]

    def branch_contains_ref(self):
        return ['git', 'branch', f'origin/{self.branch}',
                '-r', '--contains', self.commit]

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
        refspec = self.commit \
            or self.remove_ref_prefix(self.tag or self.branch or self.refspec)
        return ['git', 'checkout', '-q', '-B', f'patched-{refspec}']

    def apply_patches_file_cmd(self, path):
        return ['git', 'apply', '--whitespace=nowarn', path]

    def set_remote_url_cmd(self):
        return ['git', 'remote', 'set-url', 'origin', self.effective_url]

    def get_remote_url_cmd(self):
        return ['git', 'remote', 'get-url', 'origin']

    def get_commit_cmd(self):
        rev = self.commit or 'HEAD'
        return ['git', 'rev-parse', '--verify', rev]

    def get_patch_timestamp(self, path):
        date = linecache.getline(path, 3)
        linecache.clearcache()
        if date and date.startswith("Date: "):
            return date.replace("Date: ", "").strip()

    def contains_path_cmd(self, path):
        return ['git', 'ls-files', '--error-unmatch', path]

    def diff(self, commit1, commit2):
        if commit1 is None:
            commit1 = 'HEAD'
        if commit2 is None:
            commit2 = 'HEAD'
        git_repo = GitPythonRepo(self.path)
        shallow_file = os.path.join(git_repo.git_dir, 'shallow')
        if os.path.isfile(shallow_file):
            git_repo.git.fetch(unshallow=True)
        commits = list(git_repo.iter_commits(
                       f'{commit1}..{commit2}'))
        diff_json = {self.name: []}
        for commit in commits:
            diff_json[self.name].append({
                'commit': commit.hexsha,
                'author': commit.author.name,
                'email': commit.author.email,
                'commit_date': commit.committed_datetime.
                strftime("%Y-%m-%d %H:%M:%S"),
                'message': commit.message
            })
        return diff_json


class MercurialRepo(RepoImpl):
    """
        Provides the hg functionality for a Repo.
    """

    @staticmethod
    def get_type():
        return 'hg'

    def add_cmd(self):
        return ['hg', 'add']

    def clone_cmd(self, srcdir, createref):
        # Mercurial does not support repo references (object caches)
        if createref:
            return ['true']
        return ['hg', 'clone', self.effective_url, self.path]

    def commit_cmd(self, env, author, msg, date):
        return ['hg', 'commit', '--user', author, '-m', msg, '--date', date]

    def contains_refspec_cmd(self):
        return ['hg', 'log', '-r', self.commit or self.tag or self.branch
                or self.refspec]

    def fetch_cmd(self):
        return ['hg', 'pull']

    def is_dirty_cmd(self):
        return ['hg', 'status', '--modified', '--added',
                '--removed', '--deleted']

    def is_signed_cmd(self):
        raise NotImplementedError()

    def resolve_branch_cmd(self):
        if self.branch:
            return ['hg', 'identify', '--id', '-r',
                    f'limit(heads(branch({self.branch})))']
        else:
            return ['hg', 'identify', '--id', '-r', self.refspec]

    def resolve_tag_cmd(self):
        refspec = self.tag or self.refspec
        return ['hg', 'identify', '--id', '-r', f'tag({refspec})']

    def branch_contains_ref(self):
        return ['hg', 'log', '-r', self.commit, '-b', self.branch]

    def checkout_cmd(self, desired_ref, is_branch):
        cmd = ['hg', 'checkout', desired_ref]
        if get_context().force_checkout:
            cmd.append('--clean')
        return cmd

    def prepare_patches_cmd(self):
        refspec = (self.commit or self.tag or self.branch or self.refspec)
        # strip revision part from refspec as not allowed in branch names
        refspec = refspec.split(':')[-1]
        return ['hg', 'branch', '-f', f'patched-{refspec}']

    def apply_patches_file_cmd(self, path):
        return ['hg', 'import', '--no-commit', path]

    def set_remote_url_cmd(self):
        raise NotImplementedError()

    def get_remote_url_cmd(self):
        return ['hg', 'paths', 'default']

    def get_commit_cmd(self):
        rev = self.commit or '.'
        return ['hg', 'log', '-r', rev, '--template', '{node}\n']

    def get_patch_timestamp(self, path):
        date = None
        if linecache.getline(path, 3).startswith("# Date "):
            date = linecache.getline(path, 4)
        linecache.clearcache()

        if date and date.startswith("# "):
            return date.replace("# ", "").strip()

    def contains_path_cmd(self, path):
        return ['hg', 'files', path]

    def diff(self, commit1, commit2):
        raise NotImplementedError("Unsupported diff for MercurialRepo")
