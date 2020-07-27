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
    This module contains the implementation of the kas configuration.
"""

import os
from .repos import Repo
from .includehandler import IncludeHandler, IncludeException

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Config:
    """
        Implements the kas configuration based on config files.
    """
    def __init__(self, filename, target, task=None):
        self._override_target = target
        self._override_task = task
        self._config = {}
        self.filenames = [os.path.abspath(configfile)
                          for configfile in filename.split(':')]

        repo_paths = [Repo.get_root_path(os.path.dirname(configfile),
                                         fallback=False)
                      for configfile in self.filenames]
        if len(set(repo_paths)) > 1:
            raise IncludeException('All concatenated config files must '
                                   'belong to the same repository or all '
                                   'must be outside of versioning control')

        self.handler = IncludeHandler(self.filenames)
        self.repo_dict = self._get_repo_dict()

    def find_missing_repos(self):
        """
            Returns repos that are in config but not on disk
        """
        repo_paths = {}
        (self._config, missing_repo_names) = \
            self.handler.get_config(repos=repo_paths)

        return missing_repo_names

    def get_repos(self):
        """
            Returns the list of repos.
        """

        # Always keep repo_dict and repos synchronous
        # when calling get_repos
        self.repo_dict = self._get_repo_dict()
        return list(self.repo_dict.values())

    def _get_repo_dict(self):
        """
            Returns a dictionary containing the repositories with
            their names (as it is defined in the config file) as keys
            and the `Repo` instances as values.
        """
        repo_config_dict = self._config.get('repos', {})
        repo_defaults = self._config.get('defaults', {}).get('repos', {})
        repo_dict = {}
        repo_fallback_path = os.path.dirname(self.filenames[0])
        for repo in repo_config_dict:
            repo_config_dict[repo] = repo_config_dict[repo] or {}
            repo_dict[repo] = Repo.factory(repo,
                                           repo_config_dict[repo],
                                           repo_defaults,
                                           repo_fallback_path)

        return repo_dict

    def get_bitbake_targets(self):
        """
            Returns a list of bitbake targets
        """
        if self._override_target:
            return self._override_target
        environ_targets = [i
                           for i in os.environ.get('KAS_TARGET', '').split()
                           if i]
        if environ_targets:
            return environ_targets
        target = self._config.get('target', 'core-image-minimal')
        if isinstance(target, str):
            return [target]
        return target

    def get_bitbake_task(self):
        """
            Returns the bitbake task
        """
        if self._override_task:
            return self._override_task
        return os.environ.get('KAS_TASK',
                              self._config.get('task', 'build'))

    def _get_conf_header(self, header_name):
        """
            Returns the local.conf header
        """
        header = ''
        for key, value in sorted(self._config.get(header_name, {}).items()):
            header += '# {}\n{}\n'.format(key, value)
        return header

    def get_bblayers_conf_header(self):
        """
            Returns the bblayers.conf header
        """
        return self._get_conf_header('bblayers_conf_header')

    def get_local_conf_header(self):
        """
            Returns the local.conf header
        """
        return self._get_conf_header('local_conf_header')

    def get_machine(self):
        """
            Returns the machine
        """
        return os.environ.get('KAS_MACHINE',
                              self._config.get('machine', 'qemux86-64'))

    def get_distro(self):
        """
            Returns the distro
        """
        return os.environ.get('KAS_DISTRO',
                              self._config.get('distro', 'poky'))

    def get_environment(self):
        """
            Returns the configured environment variables from the configuration
            file with possible overwritten values from the environment.
        """
        env = self._config.get('env', {})
        return {var: os.environ.get(var, env[var]) for var in env}

    def get_multiconfig(self):
        """
            Returns the multiconfig array as bitbake string
        """
        multiconfigs = []
        for target in self.get_bitbake_targets():
            if target.startswith('multiconfig:') or target.startswith('mc:'):
                multiconfigs.append(target.split(':')[1])
        return ' '.join(multiconfigs)
