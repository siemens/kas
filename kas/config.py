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
import errno

try:
    from distro import id as get_distro_id
except ImportError:
    import platform

    def get_distro_id():
        """
            Wrapper around platform.dist to simulate distro.id
            platform.dist is deprecated and will be removed in python 3.7
            Use the 'distro' package instead.
        """
        # pylint: disable=deprecated-method
        return platform.dist()[0]

from .repos import Repo
from .libkas import run_cmd, repos_fetch, repo_checkout

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Config:
    """
        This is an abstract class, that defines the interface of the
        kas configuration.
    """
    def __init__(self):
        self.__kas_work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())
        self.environ = {}
        self._config = {}

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
        distro_id = get_distro_id()
        if distro_id.lower() in ['fedora', 'suse', 'opensuse']:
            self.environ = {'LC_ALL': 'en_US.utf8',
                            'LANG': 'en_US.utf8',
                            'LANGUAGE': 'en_US'}
        elif distro_id.lower() in ['debian', 'ubuntu']:
            self.environ = {'LC_ALL': 'en_US.UTF-8',
                            'LANG': 'en_US.UTF-8',
                            'LANGUAGE': 'en_US:en'}
        else:
            logging.warning('kas: Unsupported distro. No default locales set.')
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
                                 'no_proxy']}

    def get_repos(self):
        """
            Returns the list of repos.
        """
        # pylint: disable=no-self-use

        return []

    def pre_hook(self, fname):
        """
            Returns a function that is executed before every command or None.
        """
        # pylint: disable=unused-argument

        pass

    def post_hook(self, fname):
        """
            Returs a function that is executed after every command or None.
        """
        # pylint: disable=unused-argument

        pass

    def get_hook(self, fname):
        """
            Returns a function that is executed instead of the command or None.
        """
        # pylint: disable=unused-argument

        pass

    def get_bitbake_target(self):
        """
            Return the bitbake target
        """
        return os.environ.get('KAS_TARGET',
                              self._config.get('target',
                                               'core-image-minimal'))

    def _get_conf_header(self, header_name):
        """
            Returns the local.conf header
        """
        header = ''
        for key, value in self._config.get(header_name, {}).items():
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

    def get_gitlabci_config(self):
        """
            Returns the GitlabCI configuration
        """
        return self._config.get('gitlabci_config', '')


class ConfigPython(Config):
    """
        Implementation of a configuration that uses a Python script.
    """
    def __init__(self, filename, target):
        # pylint: disable=exec-used

        super().__init__()
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename) as fds:
                env = {}
                data = fds.read()
                exec(data, env)
                self._config = env
        except IOError:
            raise IOError(errno.ENOENT, os.strerror(errno.ENOENT),
                          self.filename)

        self.create_config(target)
        self.setup_environ()

    def __str__(self):
        output = 'target: {}\n'.format(self.target)
        output += 'repos:\n'
        for repo in self.get_repos():
            output += '  {}\n'.format(repo.__str__())
        output += 'environ:\n'
        for key, value in self.environ.items():
            output += '  {} = {}\n'.format(key, value)
        output += 'proxy:\n'
        for key, value in self.get_proxy_config().items():
            output += '  {} = {}\n'.format(key, value)
        return output

    def pre_hook(self, fname):
        try:
            self._config[fname + '_prepend'](self)
        except KeyError:
            pass

    def post_hook(self, fname):
        try:
            self._config[fname + '_append'](self)
        except KeyError:
            pass

    def get_hook(self, fname):
        try:
            return self._config[fname]
        except KeyError:
            return None

    def create_config(self, target):
        """
            Sets the configuration for `target`
        """
        self.target = 'core-image-minimal' if target is None else target
        self.repos = self._config['get_repos'](self, target)

    def get_proxy_config(self):
        return self._config['get_proxy_config']()

    def get_repos(self):
        return iter(self.repos)

    def get_target(self):
        """
            Returns the target
        """
        return self.target

    def get_bitbake_target(self):
        """
            Return the bitbake target
        """
        try:
            return self._config['get_bitbake_target'](self)
        except KeyError:
            return self.target

    def get_bblayers_conf_header(self):
        """
            Returns the bblayers.conf header
        """
        try:
            return self._config['get_bblayers_conf_header']()
        except KeyError:
            return ''

    def get_local_conf_header(self):
        """
            Returns the local.conf header
        """
        try:
            return self._config['get_local_conf_header']()
        except KeyError:
            return ''

    def get_machine(self):
        """
            Returns the machine
        """
        try:
            return self._config['get_machine'](self)
        except KeyError:
            return 'qemu'

    def get_distro(self):
        """
            Returns the distro
        """
        try:
            return self._config['get_distro'](self)
        except KeyError:
            return 'poky'

    def get_gitlabci_config(self):
        """
            Returns the GitlabCI configuration
        """
        try:
            return self._config['get_gitlabci_config'](self)
        except KeyError:
            return ''


class ConfigStatic(Config):
    """
        Implements the static kas configuration based on config files.
    """

    def __init__(self, filename, target):
        from .includehandler import GlobalIncludes, IncludeException
        super().__init__()
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

            repo_dict = self.get_repo_dict()
            missing_repos = [repo_dict[repo_name]
                             for repo_name in missing_repo_names
                             if repo_name in repo_dict]

            repos_fetch(self, missing_repos)

            for repo in missing_repos:
                repo_checkout(self, repo)

            repo_paths = {r: repo_dict[r].path for r in repo_dict}

            missing_repo_names_old = missing_repo_names
            (self._config, missing_repo_names) = \
                self.handler.get_config(repos=repo_paths)

        if target:
            self._config['target'] = target

    def get_repos(self):
        """
            Returns the list of repos.
        """
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
            layers_dict = repo_config_dict[repo].get('layers', {})
            layers = list(filter(lambda x, laydict=layers_dict:
                                 str(laydict[x]).lower() not in
                                 ['disabled', 'excluded', 'n', 'no', '0',
                                  'false'],
                                 layers_dict))
            url = repo_config_dict[repo].get('url', None)
            name = repo_config_dict[repo].get('name', repo)
            refspec = repo_config_dict[repo].get('refspec', None)
            path = repo_config_dict[repo].get('path', None)

            if url is None:
                # No git operation on repository
                if path is None:
                    # In-tree configuration
                    path = os.path.dirname(self.filename)
                    (_, output) = run_cmd(['/usr/bin/git',
                                           'rev-parse',
                                           '--show-toplevel'],
                                          cwd=path,
                                          env=self.environ)
                    path = output.strip()

                url = path
                rep = Repo(url=url,
                           path=path,
                           layers=layers)
                rep.disable_git_operations()
            else:
                path = path or os.path.join(self.kas_work_dir, name)
                rep = Repo(url=url,
                           path=path,
                           refspec=refspec,
                           layers=layers)
            repo_dict[repo] = rep
        return repo_dict


def load_config(filename, target):
    """
        Return configuration generated from `filename`.
    """

    (_, ext) = os.path.splitext(filename)
    if ext == '.py':
        cfg = ConfigPython(filename, target)
    else:
        cfg = ConfigStatic(filename, target)

    return cfg
