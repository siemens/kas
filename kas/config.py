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
import sys
import logging
import errno
import json
import yaml

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
from .libkas import run_cmd

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
        if distro_id in ['fedora', 'SuSE']:
            self.environ = {'LC_ALL': 'en_US.utf8',
                            'LANG': 'en_US.utf8',
                            'LANGUAGE': 'en_US'}
        elif distro_id in ['Ubuntu', 'debian']:
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
        """
            Returns a function that is executed before every command or None.
        """
        try:
            self._config[fname + '_prepend'](self)
        except KeyError:
            pass

    def post_hook(self, fname):
        """
            Returs a function that is executed after every command or None.
        """
        try:
            self._config[fname + '_append'](self)
        except KeyError:
            pass

    def get_hook(self, fname):
        """
            Returns a function that is executed instead of the command or None.
        """
        try:
            return self._config[fname]
        except KeyError:
            return None

    def create_config(self, target):
        """
            Sets the configuration for `target`
        """
        self.target = target
        self.repos = self._config['get_repos'](self, target)

    def get_proxy_config(self):
        """
            Returns the proxy settings
        """
        return self._config['get_proxy_config']()

    def get_repos(self):
        """
            Returns the list of repos
        """
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
        An abstract class for static configuration files
    """

    def __init__(self, filename, _):
        super().__init__()
        self.filename = os.path.abspath(filename)
        self._config = {}

    def pre_hook(self, _):
        """
            Not used
        """
        pass

    def post_hook(self, _):
        """
            Not used
        """
        pass

    def get_hook(self, _):
        """
            Not used
        """
        pass

    def get_proxy_config(self):
        """
            Returns the proxy settings
        """
        try:
            return self._config['proxy_config']
        except KeyError:
            return {'http_proxy': os.environ.get('http_proxy', ''),
                    'https_proxy': os.environ.get('https_proxy', ''),
                    'no_proxy': os.environ.get('no_proxy', '')}

    def get_repos(self):
        """
            Returns the list of repos
        """
        repos = []
        for repo in self._config['repos']:
            try:
                layers = repo['layers']
            except KeyError:
                layers = None

            url = repo['url']
            if url == '':
                # in-tree configuration
                (_, output) = run_cmd(['/usr/bin/git',
                                       'rev-parse',
                                       '--show-toplevel'],
                                      cwd=os.path.dirname(self.filename),
                                      env=self.environ)
                url = output.strip()
                rep = Repo(url=url,
                           path=url,
                           layers=layers)
                rep.disable_git_operations()
            else:
                name = os.path.basename(os.path.splitext(url)[0])
                rep = Repo(url=url,
                           path=os.path.join(self.kas_work_dir, name),
                           refspec=repo['refspec'],
                           layers=layers)
            repos.append(rep)

        return repos

    def get_bitbake_target(self):
        """
            Return the bitbake target
        """
        try:
            return self._config['target']
        except KeyError:
            return 'core-image-minimal'

    def get_bblayers_conf_header(self):
        """
            Returns the bblayers.conf header
        """
        try:
            return self._config['bblayers_conf_header']
        except KeyError:
            return ''

    def get_local_conf_header(self):
        """
            Returns the local.conf header
        """
        try:
            return self._config['local_conf_header']
        except KeyError:
            return ''

    def get_machine(self):
        """
            Returns the machine
        """
        try:
            return self._config['machine']
        except KeyError:
            return 'qemu'

    def get_distro(self):
        """
            Returns the distro
        """
        try:
            return self._config['distro']
        except KeyError:
            return 'poky'

    def get_gitlabci_config(self):
        """
            Returns the GitlabCI configuration
        """
        try:
            return self._config['gitlabci_config']
        except KeyError:
            return ''


class ConfigJson(ConfigStatic):
    """
        Implements the configuration based on JSON files
    """

    def __init__(self, filename, target):
        super().__init__(filename, target)
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename, 'r') as fds:
                self._config = json.load(fds)
        except json.decoder.JSONDecodeError as msg:
            logging.error('Could not load JSON config: %s', msg)
            sys.exit(1)
        self.setup_environ()

    def get_bblayers_conf_header(self):
        header_list = super().get_bblayers_conf_header()
        conf = ''
        for line in header_list:
            conf += str(line) + '\n'
        return conf

    def get_local_conf_header(self):
        header_list = super().get_local_conf_header()
        conf = ''
        for line in header_list:
            conf += str(line) + '\n'
        return conf


class ConfigYaml(ConfigStatic):
    """
        Implements  the configuration based on Yaml files
    """

    def __init__(self, filename, target):
        super().__init__(filename, target)
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename, 'r') as fds:
                self._config = yaml.load(fds)
        except yaml.loader.ParserError as msg:
            logging.error('Could not load YAML config: %s', msg)
            sys.exit(1)
        self.setup_environ()


def load_config(filename, target):
    """
        Return configuration generated from `filename`.
    """
    # pylint: disable=redefined-variable-type

    (_, ext) = os.path.splitext(filename)
    if ext == '.py':
        cfg = ConfigPython(filename, target)
    elif ext == '.json':
        cfg = ConfigJson(filename, target)
    elif ext == '.yml':
        cfg = ConfigYaml(filename, target)
    else:
        logging.error('Config file extenstion not recognized')
        sys.exit(1)

    return cfg
