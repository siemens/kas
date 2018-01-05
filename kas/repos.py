# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017
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

import os
import asyncio
import logging
from urllib.parse import urlparse
from .libkas import run_cmd_async, run_cmd

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Repo:
    """
        Represents a repository in the kas configuration.
    """

    def __init__(self, url, path, refspec, layers, disable_operations):
        # pylint: disable=too-many-arguments
        self.url = url
        self.path = path
        self.refspec = refspec
        self._layers = layers
        self.name = os.path.basename(self.path)
        self.operations_disabled = disable_operations

    def __getattr__(self, item):
        if item == 'layers':
            if not self._layers:
                return [self.path]
            return [self.path + '/' + l for l in self._layers]
        elif item == 'qualified_name':
            url = urlparse(self.url)
            return ('{url.netloc}{url.path}'
                    .format(url=url)
                    .replace('@', '.')
                    .replace(':', '.')
                    .replace('/', '.')
                    .replace('*', '.'))
        else:
            # Default behaviour
            raise AttributeError

    def __str__(self):
        return '%s:%s %s %s' % (self.url, self.refspec,
                                self.path, self._layers)

    @staticmethod
    def factory(url, path, typ, refspec, layers, disable_operations):
        """
            Return an instance Repo depending on params.
        """
        # pylint: disable=too-many-arguments
        if typ == 'git':
            return GitRepo(url, path, refspec, layers, disable_operations)
        raise NotImplementedError('Repo typ "%s" not supported.' % typ)

    @staticmethod
    def get_root_path(path, environ):
        """
            Check if path is a version control repo and return its root path.
        """
        (ret, output) = run_cmd(['git',
                                 'rev-parse',
                                 '--show-toplevel'],
                                cwd=path,
                                env=environ,
                                fail=False,
                                liveupdate=False)
        if ret == 0:
            return output.strip()

        return path


class GitRepo(Repo):
    """
        Provides the git implementations for a Repo.
    """

    @asyncio.coroutine
    def fetch_async(self, config):
        """
            Start asynchronous repository fetch.
        """
        if self.operations_disabled:
            return 0

        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            gitsrcdir = os.path.join(config.get_repo_ref_dir() or '',
                                     self.qualified_name)
            logging.debug('Looking for repo ref dir in %s', gitsrcdir)

            cmd = ['git', 'clone', '-q', self.url, self.path]
            if config.get_repo_ref_dir() and os.path.exists(gitsrcdir):
                cmd.extend(['--reference', gitsrcdir])
            (retc, _) = yield from run_cmd_async(cmd,
                                                 env=config.environ,
                                                 cwd=config.kas_work_dir)
            if retc == 0:
                logging.info('Repository %s cloned', self.name)
            return retc

        # take what came out of clone and stick to that forever
        if self.refspec is None:
            return 0

        # Does refspec exist in the current repository?
        (retc, output) = yield from run_cmd_async(['git',
                                                   'cat-file', '-t',
                                                   self.refspec],
                                                  env=config.environ,
                                                  cwd=self.path,
                                                  fail=False,
                                                  liveupdate=False)
        if retc == 0:
            logging.info('Repository %s already contains %s as %s',
                         self.name, self.refspec, output.strip())
            return retc

        # No it is missing, try to fetch
        (retc, output) = yield from run_cmd_async(['git',
                                                   'fetch', '--all'],
                                                  env=config.environ,
                                                  cwd=self.path,
                                                  fail=False)
        if retc:
            logging.warning('Could not update repository %s: %s',
                            self.name, output)
        else:
            logging.info('Repository %s updated', self.name)
        return 0

    def checkout(self, config):
        """
            Checks out the correct revision of the repo.
        """
        if self.operations_disabled or self.refspec is None:
            return

        # Check if repos is dirty
        (_, output) = run_cmd(['git', 'diff', '--shortstat'],
                              env=config.environ, cwd=self.path,
                              fail=False)
        if output:
            logging.warning('Repo %s is dirty. no checkout', self.name)
            return

        # Check if current HEAD is what in the config file is defined.
        (_, output) = run_cmd(['git', 'rev-parse',
                               '--verify', 'HEAD'],
                              env=config.environ, cwd=self.path)

        if output.strip() == self.refspec:
            logging.info('Repo %s has already checkout out correct '
                         'refspec. nothing to do', self.name)
            return

        run_cmd(['git', 'checkout', '-q',
                 '{refspec}'.format(refspec=self.refspec)],
                cwd=self.path)
