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
from .config import Config, get_distro_id_base


# pylint: disable=too-many-instance-attributes
class Context:
    """
        Implements the kas build context.
    """
    def __init__(self, config_filename, bitbake_target, bitbake_task):
        self.config_filename = config_filename
        self.bitbake_target = bitbake_target
        self.bitbake_task = bitbake_task
        self.__kas_work_dir = os.environ.get('KAS_WORK_DIR', os.getcwd())
        self.__kas_repo_ref_dir = os.environ.get('KAS_REPO_REF_DIR', None)

        self.setup_initial_environ()
        self.keep_config = False

        self.config = Config(config_filename, bitbake_target, bitbake_task)
        self.config.set_context(self)

    def setup_initial_environ(self):
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

        for key in ['http_proxy', 'https_proxy', 'ftp_proxy', 'no_proxy']:
            val = os.environ.get(key, None)
            if val:
                self.environ[key] = val

    @property
    def build_dir(self):
        """
            The path of the build directory
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
