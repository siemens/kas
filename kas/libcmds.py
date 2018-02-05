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
    This module contain common commands used by kas plugins.
"""

import tempfile
import logging
import shutil
import os
from .libkas import (ssh_cleanup_agent, ssh_setup_agent, ssh_no_host_key_check,
                     get_build_environ, repos_fetch)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Macro:
    """
        Contains commands and provide method to run them.
    """
    def __init__(self):
        self.commands = []

    def add(self, command):
        """
            Appends commands to the command list.
        """
        self.commands.append(command)

    def run(self, config, skip=None):
        """
            Runs command from the command list respective to the configuration.
        """
        skip = skip or []
        for command in self.commands:
            command_name = str(command)
            if command_name in skip:
                continue
            logging.debug('execute %s', command_name)
            command.execute(config)


class Command:
    """
        An abstract class that defines the interface of a command.
    """

    def execute(self, config):
        """
            This method executes the command.
        """
        pass


class SetupHome(Command):
    """
        Setups the home directory of kas.
    """

    def __init__(self):
        super().__init__()
        self.tmpdirname = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdirname)

    def __str__(self):
        return 'setup_home'

    def execute(self, config):
        with open(self.tmpdirname + '/.wgetrc', 'w') as fds:
            fds.write('\n')
        with open(self.tmpdirname + '/.netrc', 'w') as fds:
            fds.write('\n')
        config.environ['HOME'] = self.tmpdirname


class SetupDir(Command):
    """
        Creates the build directory.
    """

    def __str__(self):
        return 'setup_dir'

    def execute(self, config):
        os.chdir(config.kas_work_dir)
        if not os.path.exists(config.build_dir):
            os.mkdir(config.build_dir)


class SetupSSHAgent(Command):
    """
        Setup the ssh agent configuration.
    """

    def __str__(self):
        return 'setup_ssh_agent'

    def execute(self, config):
        ssh_setup_agent(config)
        ssh_no_host_key_check(config)


class CleanupSSHAgent(Command):
    """
        Remove all the identities and stop the ssh-agent instance.
    """

    def __str__(self):
        return 'cleanup_ssh_agent'

    def execute(self, config):
        ssh_cleanup_agent(config)


class SetupProxy(Command):
    """
        Setups proxy configuration in the kas environment.
    """

    def __str__(self):
        return 'setup_proxy'

    def execute(self, config):
        config.environ.update(config.get_proxy_config())


class SetupEnviron(Command):
    """
        Setups the kas environment.
    """

    def __str__(self):
        return 'setup_environ'

    def execute(self, config):
        config.environ.update(get_build_environ(config, config.build_dir))


class WriteConfig(Command):
    """
        Writes bitbake configuration files into the build directory.
    """

    def __str__(self):
        return 'write_config'

    def execute(self, config):
        def _write_bblayers_conf(config):
            filename = config.build_dir + '/conf/bblayers.conf'
            if not os.path.isdir(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            with open(filename, 'w') as fds:
                fds.write(config.get_bblayers_conf_header())
                fds.write('BBLAYERS ?= " \\\n    ')
                fds.write(' \\\n    '.join(
                    sorted(layer for repo in config.get_repos()
                           for layer in repo.layers)))
                fds.write('"\n')

        def _write_local_conf(config):
            filename = config.build_dir + '/conf/local.conf'
            with open(filename, 'w') as fds:
                fds.write(config.get_local_conf_header())
                fds.write('MACHINE ??= "{}"\n'.format(config.get_machine()))
                fds.write('DISTRO ??= "{}"\n'.format(config.get_distro()))
                fds.write('BBMULTICONFIG ?= "{}"\n'.format(
                    config.get_multiconfig()))

        _write_bblayers_conf(config)
        _write_local_conf(config)


class ReposFetch(Command):
    """
        Fetches repositories defined in the configuration
    """

    def __str__(self):
        return 'repos_fetch'

    def execute(self, config):
        repos_fetch(config, config.get_repos())


class ReposCheckout(Command):
    """
        Ensures that the right revision of each repo is check out.
    """

    def __str__(self):
        return 'repos_checkout'

    def execute(self, config):
        for repo in config.get_repos():
            repo.checkout(config)
