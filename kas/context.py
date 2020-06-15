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

import os
import logging

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
        return platform.dist()[0]


__context__ = None


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


class Context:
    """
        Implements the kas build context.
    """
    def __init__(self, args):
        self.__kas_work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())
        self.__kas_repo_ref_dir = os.environ.get('KAS_REPO_REF_DIR', None)
        self.setup_initial_environ()
        self.keep_config = False
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
                    'SSH_AUTH_SOCK']:
            val = os.environ.get(key, None)
            if val:
                self.environ[key] = val

    @property
    def build_dir(self):
        """
            The path to the build directory
        """
        return os.path.join(self.__kas_work_dir, 'build')

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
