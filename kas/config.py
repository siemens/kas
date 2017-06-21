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

import os
import sys
import logging
import errno
import json
import platform
import yaml
from .repos import Repo
from .libkas import run_cmd

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Config:
    def __init__(self):
        self.__kas_work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())

    @property
    def build_dir(self):
        return os.path.join(self.__kas_work_dir, 'build')

    @property
    def kas_work_dir(self):
        return self.__kas_work_dir

    def setup_environ(self):
        (distro, version, id) = platform.dist()
        if distro in ['fedora', 'SuSE']:
            self.environ = {'LC_ALL': 'en_US.utf8',
                            'LANG': 'en_US.utf8',
                            'LANGUAGE': 'en_US'}
        elif distro in ['Ubuntu', 'debian']:
            self.environ = {'LC_ALL': 'en_US.UTF-8',
                            'LANG': 'en_US.UTF-8',
                            'LANGUAGE': 'en_US:en'}
        else:
            logging.warning('kas: Unsupported distro. No default locales set.')
            self.environ = {}

    def get_repo_ref_dir(self):
        return os.environ.get('KAS_REPO_REF_DIR', None)


class ConfigPython(Config):
    def __init__(self, filename, target):
        super().__init__()
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename) as file:
                env = {}
                data = file.read()
                exec(data, env)
                self._config = env
        except IOError:
            raise IOError(errno.ENOENT, os.strerror(errno.ENOENT),
                          self.filename)

        self.create_config(target)
        self.setup_environ()

    def __str__(self):
        s = 'target: {}\n'.format(self.target)
        s += 'repos:\n'
        for r in self.get_repos():
            s += '  {}\n'.format(r.__str__())
        s += 'environ:\n'
        for k, v in self.environ.items():
            s += '  {} = {}\n'.format(k, v)
        s += 'proxy:\n'
        for k, v in self.get_proxy_config().items():
            s += '  {} = {}\n'.format(k, v)
        return s

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
        self.target = target
        self.repos = self._config['get_repos'](self, target)

    def get_proxy_config(self):
        return self._config['get_proxy_config']()

    def get_repos(self):
        return iter(self.repos)

    def get_target(self):
        return self.target

    def get_bitbake_target(self):
        try:
            return self._config['get_bitbake_target'](self)
        except KeyError:
            return self.target

    def get_bblayers_conf_header(self):
        try:
            return self._config['get_bblayers_conf_header']()
        except KeyError:
            return ''

    def get_local_conf_header(self):
        try:
            return self._config['get_local_conf_header']()
        except:
            return ''

    def get_machine(self):
        try:
            return self._config['get_machine'](self)
        except KeyError:
            return 'qemu'

    def get_distro(self):
        try:
            return self._config['get_distro'](self)
        except KeyError:
            return 'poky'

    def get_gitlabci_config(self):
        try:
            return self._config['get_gitlabci_config'](self)
        except KeyError:
            return ''


class ConfigStatic(Config):
    def __init__(self, filename, target):
        super().__init__()
        self.filename = os.path.abspath(filename)
        self._config = []

    def pre_hook(self, target):
        pass

    def post_hook(self, target):
        pass

    def get_hook(self, fname):
        return None

    def get_proxy_config(self):
        try:
            return self._config['proxy_config']
        except KeyError:
            return {'http_proxy': os.environ.get('http_proxy', ''),
                    'https_proxy': os.environ.get('https_proxy', ''),
                    'no_proxy': os.environ.get('no_proxy', '')}

    def get_repos(self):
        repos = []
        for repo in self._config['repos']:
            try:
                sublayers = repo['sublayers']
            except KeyError:
                sublayers = None

            url = repo['url']
            if url == '':
                # in-tree configuration
                (rc, output) = run_cmd(['/usr/bin/git',
                                        'rev-parse',
                                        '--show-toplevel'],
                                       cwd=os.path.dirname(self.filename),
                                       env=self.environ)
                url = output.strip()
                r = Repo(url=url,
                         path=url,
                         sublayers=sublayers)
                r.disable_git_operations()
            else:
                name = os.path.basename(os.path.splitext(url)[0])
                r = Repo(url=url,
                         path=os.path.join(self.kas_work_dir, name),
                         refspec=repo['refspec'],
                         sublayers=sublayers)
            repos.append(r)

        return repos

    def get_bitbake_target(self):
        try:
            return self._config['target']
        except KeyError:
            return 'core-image-minimal'

    def get_bblayers_conf_header(self):
        try:
            return self._config['bblayers_conf_header']
        except KeyError:
            return ''

    def get_local_conf_header(self):
        try:
            return self._config['local_conf_header']
        except KeyError:
            return ''

    def get_machine(self):
        try:
            return self._config['machine']
        except KeyError:
            return 'qemu'

    def get_distro(self):
        try:
            return self._config['distro']
        except KeyError:
            return 'poky'

    def get_gitlabci_config(self):
        try:
            return self._config['gitlabci_config']
        except KeyError:
            return ''


class ConfigJson(ConfigStatic):
    def __init__(self, filename, target):
        super().__init__(filename, target)
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename, 'r') as f:
                self._config = json.load(f)
        except json.decoder.JSONDecodeError as msg:
            logging.error('Could not load JSON config: {}'.format(msg))
            sys.exit(1)
        self.setup_environ()

    def get_bblayers_conf_header(self):
        list = super().get_bblayers_conf_header()
        conf = ''
        for line in list:
            conf += str(line) + '\n'
        return conf

    def get_local_conf_header(self):
        list = super().get_local_conf_header()
        conf = ''
        for line in list:
            conf += str(line) + '\n'
        return conf


class ConfigYaml(ConfigStatic):
    def __init__(self, filename, target):
        super().__init__(filename, target)
        self.filename = os.path.abspath(filename)
        try:
            with open(self.filename, 'r') as f:
                self._config = yaml.load(f)
        except yaml.loader.ParserError as msg:
            logging.error('Could not load YAML config: {}'.format(msg))
            sys.exit(1)
        self.setup_environ()


def load_config(filename, target):
    f, ext = os.path.splitext(filename)
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
