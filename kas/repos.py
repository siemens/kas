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
from .context import get_context
from .libkas import run_cmd_async, run_cmd

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Repo:
    """
        Represents a repository in the kas configuration.
    """

    def __init__(self, url, path, refspec, layers, patches,
                 disable_operations):
        self.url = url
        self.path = path
        self.refspec = refspec
        self._layers = layers
        self._patches = patches
        self.name = os.path.basename(self.path)
        self.operations_disabled = disable_operations

    def __getattr__(self, item):
        if item == 'layers':
            return [os.path.join(self.path, layer) for layer in self._layers]
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
        # Default behaviour
        raise AttributeError

    def __str__(self):
        return '%s:%s %s %s' % (self.url, self.refspec,
                                self.path, self._layers)

    @staticmethod
    def factory(name, repo_config, repo_defaults, repo_fallback_path):
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
                logging.error('No repo specified for patch entry "%s" and no '
                              'default repo specified.', p)
                sys.exit(1)
            patches.append(this_patch)

        url = repo_config.get('url', None)
        name = repo_config.get('name', name)
        typ = repo_config.get('type', 'git')
        refspec = repo_config.get('refspec',
                                  repo_defaults.get('refspec', None))
        path = repo_config.get('path', None)
        disable_operations = False

        if url is None:
            # No version control operation on repository
            if path is None:
                path = Repo.get_root_path(repo_fallback_path)
                logging.info('Using %s as root for repository %s', path,
                             name)

            url = path
            disable_operations = True
        else:
            if path is None:
                path = os.path.join(get_context().kas_work_dir, name)
            else:
                if not os.path.isabs(path):
                    # Relative pathes are assumed to start from work_dir
                    path = os.path.join(get_context().kas_work_dir, path)

        if typ == 'git':
            return GitRepo(url, path, refspec, layers, patches,
                           disable_operations)
        if typ == 'hg':
            return MercurialRepo(url, path, refspec, layers, patches,
                                 disable_operations)
        raise NotImplementedError('Repo type "%s" not supported.' % typ)

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

        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            sdir = os.path.join(get_context().kas_repo_ref_dir or '',
                                self.qualified_name)
            logging.debug('Looking for repo ref dir in %s', sdir)

            (retc, _) = await run_cmd_async(
                self.clone_cmd(sdir),
                cwd=get_context().kas_work_dir)
            if retc == 0:
                logging.info('Repository %s cloned', self.name)
            return retc

        # Make sure the remote origin is set to the value
        # in the kas file to avoid suprises
        try:
            (retc, output) = await run_cmd_async(
                self.set_remote_url_cmd(),
                cwd=self.path,
                fail=False,
                liveupdate=False)
            if retc != 0:
                logging.info('Changing remote URL to %s failed with error: %s',
                             self.effective_url, output.strip())
                return retc
        except NotImplementedError:
            logging.warning('Repo implementation does not support changing '
                            'the remote url.')

        # take what came out of clone and stick to that forever
        if self.refspec is None:
            return 0

        if not get_context().update:
            # Does refspec exist in the current repository?
            (retc, output) = await run_cmd_async(self.contains_refspec_cmd(),
                                                 cwd=self.path,
                                                 fail=False,
                                                 liveupdate=False)
            if retc == 0:
                logging.info('Repository %s already contains %s as %s',
                             self.name, self.refspec, output.strip())
                return retc

        # Try to fetch if refspec is missing or if --update argument was passed
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
        if self.operations_disabled or self.refspec is None:
            return

        if not get_context().force_checkout:
            # Check if repos is dirty
            (_, output) = run_cmd(self.is_dirty_cmd(),
                                  cwd=self.path,
                                  fail=False)
            if output:
                logging.warning('Repo %s is dirty - no checkout', self.name)
                return

        (_, output) = run_cmd(self.resolve_branch_cmd(),
                              cwd=self.path, fail=False)
        if output:
            desired_ref = output.strip()
            branch = True
        else:
            desired_ref = self.refspec
            branch = False

        run_cmd(self.checkout_cmd(desired_ref, branch), cwd=self.path)

    async def apply_patches_async(self):
        """
            Applies patches to a repository asynchronously.
        """
        if self.operations_disabled or not self._patches:
            return 0

        (retc, _) = await run_cmd_async(self.prepare_patches_cmd(),
                                        cwd=self.path)
        if retc:
            return retc

        my_patches = []

        for patch in self._patches:
            other_repo = get_context().config.repo_dict.get(patch['repo'],
                                                            None)

            if not other_repo:
                logging.error('Could not find referenced repo. '
                              '(missing repo: %s, repo: %s, '
                              'patch entry: %s)',
                              patch['repo'],
                              self.name,
                              patch['id'])
                return 1

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
                            raise FileNotFoundError(p)
            else:
                logging.error('Could not find patch. '
                              '(patch path: %s, repo: %s, patch entry: %s)',
                              path,
                              self.name,
                              patch['id'])
                return 1

        for (path, patch_id) in my_patches:
            cmd = self.apply_patches_file_cmd(path)
            (retc, output) = await run_cmd_async(cmd, cwd=self.path)
            if retc:
                logging.error('Could not apply patch. Please fix repos and '
                              'patches. (patch path: %s, repo: %s, patch '
                              'entry: %s, vcs output: %s)',
                              path, self.name, patch_id, output)
                return 1
            else:
                logging.info('Patch applied. '
                             '(patch path: %s, repo: %s, patch entry: %s)',
                             path, self.name, patch_id)

            cmd = self.add_cmd()
            (retc, output) = await run_cmd_async(cmd, cwd=self.path)
            if retc:
                logging.error('Could not add patched files. '
                              'repo: %s, vcs output: %s)',
                              self.name, output)
                return 1

            cmd = self.commit_cmd()
            (retc, output) = await run_cmd_async(cmd, cwd=self.path)
            if retc:
                logging.error('Could not commit patch changes. '
                              'repo: %s, vcs output: %s)',
                              self.name, output)
                return 1

        return 0


class GitRepo(RepoImpl):
    """
        Provides the git functionality for a Repo.
    """

    def add_cmd(self):
        return ['git', 'add', '-A']

    def clone_cmd(self, gitsrcdir):
        cmd = ['git', 'clone', '-q', self.effective_url, self.path]
        if get_context().kas_repo_ref_dir and os.path.exists(gitsrcdir):
            cmd.extend(['--reference', gitsrcdir])
        return cmd

    def commit_cmd(self):
        return ['git', 'commit', '-a', '--author', 'kas <kas@example.com>',
                '-m', 'msg']

    def contains_refspec_cmd(self):
        return ['git', 'cat-file', '-t', self.refspec]

    def fetch_cmd(self):
        return ['git', 'fetch']

    def is_dirty_cmd(self):
        return ['git', 'status', '-s']

    def resolve_branch_cmd(self):
        return ['git', 'rev-parse', '--verify', '-q',
                'origin/{refspec}'.format(refspec=self.refspec)]

    def checkout_cmd(self, desired_ref, branch):
        cmd = ['git', 'checkout', '-q', desired_ref]
        if branch:
            cmd.extend(['-B', self.refspec])
        if get_context().force_checkout:
            cmd.append('--force')
        return cmd

    def prepare_patches_cmd(self):
        return ['git', 'checkout', '-q', '-B',
                'patched-{refspec}'.format(refspec=self.refspec)]

    def apply_patches_file_cmd(self, path):
        return ['git', 'apply', path]

    def set_remote_url_cmd(self):
        return ['git', 'remote', 'set-url', 'origin', self.effective_url]


class MercurialRepo(RepoImpl):
    """
        Provides the hg functionality for a Repo.
    """

    def add_cmd(self):
        return ['hg', 'add']

    def clone_cmd(self, srcdir):
        return ['hg', 'clone', self.effective_url, self.path]

    def commit_cmd(self):
        return ['hg', 'commit', '--user', 'kas <kas@example.com>', '-m', 'msg']

    def contains_refspec_cmd(self):
        return ['hg', 'log', '-r', self.refspec]

    def fetch_cmd(self):
        return ['hg', 'pull']

    def is_dirty_cmd(self):
        return ['hg', 'diff']

    def resolve_branch_cmd(self):
        # We never need to care about creating tracking branches in mercurial
        return ['false']

    def checkout_cmd(self, desired_ref, branch):
        cmd = ['hg', 'checkout', desired_ref]
        if get_context().force_checkout:
            cmd.append('--clean')
        return cmd

    def prepare_patches_cmd(self):
        return ['hg', 'branch', '-f',
                'patched-{refspec}'.format(refspec=self.refspec)]

    def apply_patches_file_cmd(self, path):
        return ['hg', 'import', '--no-commit', path]

    def set_remote_url_cmd(self):
        raise NotImplementedError()
