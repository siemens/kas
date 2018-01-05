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
    This module contains the implementation of the kas configuration.
"""

import os
import logging
import pprint

try:
    import distro

    def get_distro_id_base():
        """
            Returns a compatible distro id.
        """
        return distro.like() or distro.id()

except ImportError:
    import platform

    def get_distro_id_base():
        """
            Wrapper around platform.dist to simulate distro.id
            platform.dist is deprecated and will be removed in python 3.7
            Use the 'distro' package instead.
        """
        # pylint: disable=deprecated-method
        return platform.dist()[0]

from .repos import Repo
from .libkas import repos_fetch

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Config:
    """
        Implements the kas configuration based on config files.
    """
    def __init__(self, filename, target, task=None):
        from .includehandler import GlobalIncludes, IncludeException
        self.__kas_work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())
        self.environ = {}
        self._config = {}
        self.setup_environ()
        self.filename = os.path.abspath(filename)
        self.handler = GlobalIncludes(self.filename)

        repo_paths = {}
        missing_repo_names_old = []
        (self._config, missing_repo_names) = \
            self.handler.get_config(repos=repo_paths)

        self.environ.update(self.get_proxy_config())

        while missing_repo_names:
            if missing_repo_names == missing_repo_names_old:
                raise IncludeException('Could not fetch all repos needed by '
                                       'includes.')

            logging.debug('Missing repos for complete config:\n%s',
                          pprint.pformat(missing_repo_names))

            repo_dict = self.get_repo_dict()
            missing_repos = [repo_dict[repo_name]
                             for repo_name in missing_repo_names
                             if repo_name in repo_dict]

            repos_fetch(self, missing_repos)

            for repo in missing_repos:
                repo.checkout(self)

            repo_paths = {r: repo_dict[r].path for r in repo_dict}

            missing_repo_names_old = missing_repo_names
            (self._config, missing_repo_names) = \
                self.handler.get_config(repos=repo_paths)

        logging.debug('Configuration from config file:\n%s',
                      pprint.pformat(self._config))

        if target:
            self._config['target'] = target
        if task:
            self._config['task'] = task

    @property
    def build_dir(self):
        """
            The path of the build directory.
        """
        return os.path.join(self.__kas_work_dir, 'build')

    @property
    def kas_work_dir(self):
        """
            The path to the kas work directory.
        """
        return self.__kas_work_dir

    def setup_environ(self):
        """
            Sets the environment variables for process that are
            started by kas.
        """
        distro_base = get_distro_id_base().lower()
        if distro_base in ['fedora', 'suse', 'opensuse']:
            self.environ = {'LC_ALL': 'en_US.utf8',
                            'LANG': 'en_US.utf8',
                            'LANGUAGE': 'en_US'}
        elif distro_base in ['debian', 'ubuntu', 'gentoo']:
            self.environ = {'LC_ALL': 'en_US.UTF-8',
                            'LANG': 'en_US.UTF-8',
                            'LANGUAGE': 'en_US:en'}
        else:
            logging.warning('kas: "%s" is not a supported distro. '
                            'No default locales set.', distro_base)
            self.environ = {}

    def get_repo_ref_dir(self):
        """
            The path to the directory that contains the repository references.
        """
        # pylint: disable=no-self-use

        return os.environ.get('KAS_REPO_REF_DIR', None)

    def get_proxy_config(self):
        """
            Returns the proxy settings
        """
        proxy_config = self._config.get('proxy_config', {})
        return {var_name: os.environ.get(var_name,
                                         proxy_config.get(var_name, ''))
                for var_name in ['http_proxy',
                                 'https_proxy',
                                 'ftp_proxy',
                                 'no_proxy']}

    def get_repos(self):
        """
            Returns the list of repos.
        """
        # pylint: disable=no-self-use

        return list(self.get_repo_dict().values())

    def get_repo_dict(self):
        """
            Returns a dictionary containing the repositories with
            their name (as it is defined in the config file) as key
            and the `Repo` instances as value.
        """
        repo_config_dict = self._config.get('repos', {})
        repo_dict = {}
        for repo in repo_config_dict:
            repo_config_dict[repo] = repo_config_dict[repo] or {}
            repo_dict[repo] = Repo.factory(repo, repo_config_dict[repo], self)

        return repo_dict

    def get_bitbake_targets(self):
        """
            Returns a list of bitbake targets
        """
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
            Return the bitbake task
        """
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
                              self._config.get('machine', 'qemu'))

    def get_distro(self):
        """
            Returns the distro
        """
        return os.environ.get('KAS_DISTRO',
                              self._config.get('distro', 'poky'))

    def get_environment(self):
        """
            Returns the configured environment variables from the configuration
            file, with possible overwritten values from the environment.
        """
        env = self._config.get('env', {})
        return {var: os.environ.get(var, env[var]) for var in env}

    def get_multiconfig(self):
        """
            Returns the multiconfig array as bitbake string
        """
        return ' '.join(set(i.split(':')[1]
                            for i in
                            self.get_bitbake_targets()
                            if i.startswith('multiconfig')))

    def get_gitlabci_config(self):
        """
            Returns the GitlabCI configuration
        """
        return self._config.get('gitlabci_config', '')
