# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2018
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
    This module contains the implementation of the kas context.
"""

import distro
import os
import logging
from enum import Enum
from kas.kasusererror import KasUserError
from kas import __version__

__context__ = None


def get_distro_id_base():
    """
        Returns a compatible distro id.
    """
    return distro.like() or distro.id()


def create_global_context(args):
    """
        Creates global context as singleton.
    """
    global __context__
    __context__ = Context(args)
    return __context__


def get_context():
    """
        Returns singleton global context.
    """
    return __context__


class ManagedEnvironment(Enum):
    """
    Managed environments are well-known executors (like CI systems)
    that kas can detect and adapt to.
    """
    GITHUB_ACTIONS = 1
    GITLAB_CI = 2
    VSCODE_REMOTE_CONTAINERS = 3

    def __str__(self):
        if self == self.GITHUB_ACTIONS:
            return 'GitHub Actions'
        if self == self.GITLAB_CI:
            return 'GitLab CI'
        if self == self.VSCODE_REMOTE_CONTAINERS:
            return 'VSCode Remote Containers'
        return f'{self.name}'


class Context:
    """
        Implements the kas build context.
    """
    def __init__(self, args):
        work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())
        self.__kas_work_dir = os.path.abspath(work_dir)
        build_dir = os.environ.get('KAS_BUILD_DIR',
                                   os.path.join(self.__kas_work_dir, 'build'))
        self.__kas_build_dir = os.path.abspath(build_dir)
        ref_dir = os.environ.get('KAS_REPO_REF_DIR', None)
        self.__kas_repo_ref_dir = os.path.abspath(ref_dir) if ref_dir else None
        clone_depth = os.environ.get('KAS_CLONE_DEPTH', '0')
        if not clone_depth.isdigit():
            raise KasUserError('KAS_CLONE_DEPTH must be a number')
        self.repo_clone_depth = max(int(clone_depth), 0)
        self.setup_initial_environ()
        self.check_container_call()
        # Register the paths that kas created and exclusively owns
        self.managed_paths = set()
        if not os.environ.get('KAS_BUILD_DIR'):
            self.managed_paths.add(self.__kas_build_dir)
        self.keyhandler = {}
        self.config = None
        self.args = args

    def setup_initial_environ(self):
        """
            Sets the environment variables for processes that are
            started by kas.
        """
        self.environ = {}
        distro_bases = get_distro_id_base().lower().split()
        for distro_base in distro_bases:
            if distro_base in ['fedora', 'suse', 'opensuse']:
                self.environ = {'LC_ALL': 'en_US.utf8',
                                'LANG': 'en_US.utf8',
                                'LANGUAGE': 'en_US'}
                break
            elif distro_base in ['debian', 'ubuntu', 'gentoo']:
                self.environ = {'LC_ALL': 'en_US.UTF-8',
                                'LANG': 'en_US.UTF-8',
                                'LANGUAGE': 'en_US:en'}
                break
        if self.environ == {}:
            logging.warning('kas: No supported distros found in %s. '
                            'No default locales set.', distro_bases)

        for key in ['http_proxy', 'https_proxy', 'ftp_proxy', 'no_proxy',
                    'SSH_AUTH_SOCK',
                    'BB_NUMBER_THREADS', 'PARALLEL_MAKE']:
            val = os.environ.get(key, None)
            if val:
                self.environ[key] = val

        # make remote containers environment available in kas
        if self.managed_env == ManagedEnvironment.VSCODE_REMOTE_CONTAINERS:
            for k in os.environ.keys():
                if k.startswith('REMOTE_CONTAINERS_'):
                    self.environ[k] = os.environ[k]

    @staticmethod
    def check_container_call():
        container_v = os.environ.get('KAS_CONTAINER_SCRIPT_VERSION')
        if not container_v:
            # not a kas-container call (or from a too old script)
            return
        if container_v != __version__:
            logging.warning(f'kas-container ({container_v}) and '
                            f'kas ({__version__}) versions do not match')

    @staticmethod
    def _get_managed_env():
        """
            Detects if kas is running in well-known environment (e.g. a
            CI system). Returns the identifier of the CI system or None.
        """
        if os.environ.get('GITHUB_ACTIONS', False) == 'true':
            return ManagedEnvironment.GITHUB_ACTIONS
        if os.environ.get('GITLAB_CI', False) == 'true':
            return ManagedEnvironment.GITLAB_CI
        if os.environ.get('REMOTE_CONTAINERS', False) == 'true':
            return ManagedEnvironment.VSCODE_REMOTE_CONTAINERS
        return None

    @property
    def build_dir(self):
        """
            The path to the build directory
        """
        return self.__kas_build_dir

    @property
    def kas_work_dir(self):
        """
            The path to the kas work directory
        """
        return self.__kas_work_dir

    @property
    def kas_repo_ref_dir(self):
        """
            The reference directory for the repo
        """
        return self.__kas_repo_ref_dir

    @property
    def force_checkout(self):
        return getattr(self.args, 'force_checkout', None)

    @property
    def update(self):
        return getattr(self.args, 'update', None)

    @property
    def managed_env(self):
        return self._get_managed_env()
