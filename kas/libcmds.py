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
    This module contains common commands used by kas plugins.
"""

import tempfile
import logging
import shutil
import os
import pprint
from .libkas import (ssh_cleanup_agent, ssh_setup_agent, ssh_no_host_key_check,
                     get_build_environ, repos_fetch, repos_apply_patches)
from .includehandler import IncludeException

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Macro:
    """
        Contains commands and provides method to run them.
    """
    def __init__(self):
        self.commands = []

    def add(self, command):
        """
            Appends commands to the command list.
        """
        self.commands.append(command)

    def run(self, ctx, skip=None):
        """
            Runs a command from the command list with respect to the
            configuration.
        """
        skip = skip or []
        for command in self.commands:
            command_name = str(command)
            if command_name in skip:
                continue
            logging.debug('execute %s', command_name)
            command.execute(ctx)


class Command:
    """
        An abstract class that defines the interface of a command.
    """

    def execute(self, ctx):
        """
            This method executes the command.
        """
        pass


class Loop(Command):
    """
        A class that defines a set of commands as a loop.
    """
    def __init__(self, name):
        self.commands = []
        self.name = name

    def __str__(self):
        return self.name

    def add(self, command):
        """
            Appends a command to the loop.
        """
        self.commands.append(command)

    def execute(self, ctx):
        """
            Executes the loop.
        """
        loop_name = str(self)

        def executor(command):
            command_name = str(command)
            logging.debug('Loop %s: execute %s', loop_name, command_name)
            return command.execute(ctx)

        while all(executor(c) for c in self.commands):
            pass


class SetupHome(Command):
    """
        Sets up the home directory of kas.
    """

    def __init__(self):
        super().__init__()
        self.tmpdirname = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdirname)

    def __str__(self):
        return 'setup_home'

    def execute(self, ctx):
        with open(self.tmpdirname + '/.wgetrc', 'w') as fds:
            fds.write('\n')
        with open(self.tmpdirname + '/.netrc', 'w') as fds:
            fds.write('\n')
        with open(self.tmpdirname + '/.gitconfig', 'w') as fds:
            fds.write('[User]\n'
                      '\temail = kas@example.com\n'
                      '\tname = Kas User\n')

        if os.environ.get('AWS_CONFIG_FILE', False) \
                and os.environ.get('AWS_SHARED_CREDENTIALS_FILE', False):
            os.makedirs(self.tmpdirname + "/.aws")

            shutil.copy(os.environ['AWS_CONFIG_FILE'],
                        self.tmpdirname + "/.aws/config")
            shutil.copy(os.environ['AWS_SHARED_CREDENTIALS_FILE'],
                        self.tmpdirname + "/.aws/credentials")

        ctx.environ['HOME'] = self.tmpdirname


class SetupDir(Command):
    """
        Creates the build directory.
    """

    def __str__(self):
        return 'setup_dir'

    def execute(self, ctx):
        os.chdir(ctx.kas_work_dir)
        if not os.path.exists(ctx.build_dir):
            os.mkdir(ctx.build_dir)


class SetupSSHAgent(Command):
    """
        Sets up the ssh agent configuration.
    """

    def __str__(self):
        return 'setup_ssh_agent'

    def execute(self, ctx):
        ssh_setup_agent()
        ssh_no_host_key_check()


class CleanupSSHAgent(Command):
    """
        Removes all the identities and stops the ssh-agent instance.
    """

    def __str__(self):
        return 'cleanup_ssh_agent'

    def execute(self, ctx):
        ssh_cleanup_agent()


class SetupEnviron(Command):
    """
        Sets up the kas environment.
    """

    def __str__(self):
        return 'setup_environ'

    def execute(self, ctx):
        ctx.environ.update(get_build_environ())


class WriteBBConfig(Command):
    """
        Writes bitbake configuration files into the build directory.
    """

    def __str__(self):
        return 'write_bbconfig'

    def execute(self, ctx):
        def _write_bblayers_conf(ctx):
            filename = ctx.build_dir + '/conf/bblayers.conf'
            if not os.path.isdir(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            with open(filename, 'w') as fds:
                fds.write(ctx.config.get_bblayers_conf_header())
                fds.write('BBLAYERS ?= " \\\n    ')
                fds.write(' \\\n    '.join(
                    sorted(layer for repo in ctx.config.get_repos()
                           for layer in repo.layers)))
                fds.write('"\n')

        def _write_local_conf(ctx):
            filename = ctx.build_dir + '/conf/local.conf'
            with open(filename, 'w') as fds:
                fds.write(ctx.config.get_local_conf_header())
                fds.write('MACHINE ??= "{}"\n'.format(
                    ctx.config.get_machine()))
                fds.write('DISTRO ??= "{}"\n'.format(
                    ctx.config.get_distro()))
                fds.write('BBMULTICONFIG ?= "{}"\n'.format(
                    ctx.config.get_multiconfig()))

        _write_bblayers_conf(ctx)
        _write_local_conf(ctx)


class ReposFetch(Command):
    """
        Fetches repositories defined in the configuration
    """

    def __str__(self):
        return 'repos_fetch'

    def execute(self, ctx):
        repos_fetch(ctx.config.get_repos())


class ReposApplyPatches(Command):
    """
        Applies the patches defined in the configuration to the repositories.
    """

    def __str__(self):
        return 'repos_apply_patches'

    def execute(self, ctx):
        repos_apply_patches(ctx.config.get_repos())


class ReposCheckout(Command):
    """
        Ensures that the right revision of each repo is checked out.
    """

    def __str__(self):
        return 'repos_checkout'

    def execute(self, ctx):
        for repo in ctx.config.get_repos():
            repo.checkout()


class InitSetupRepos(Command):
    """
        Prepares setting up repos including the include logic
    """

    def __str__(self):
        return 'init_setup_repos'

    def execute(self, ctx):
        ctx.missing_repo_names = ctx.config.find_missing_repos()
        ctx.missing_repo_names_old = None


class SetupReposStep(Command):
    """
        Single step of the checkout repos loop
    """

    def __str__(self):
        return 'setup_repos_step'

    def execute(self, ctx):
        """ TODO refactor protected-access """
        if not ctx.missing_repo_names:
            return False

        if ctx.missing_repo_names == ctx.missing_repo_names_old:
            raise IncludeException('Could not fetch all repos needed by '
                                   'includes.')

        logging.debug('Missing repos for complete config:\n%s',
                      pprint.pformat(ctx.missing_repo_names))

        ctx.config.repo_dict = ctx.config._get_repo_dict()

        ctx.missing_repos = [ctx.config.repo_dict[repo_name]
                             for repo_name in ctx.missing_repo_names
                             if repo_name in ctx.config.repo_dict]

        repos_fetch(ctx.missing_repos)

        for repo in ctx.missing_repos:
            repo.checkout()

        ctx.config.repo_dict = ctx.config._get_repo_dict()

        repo_paths = {r: ctx.config.repo_dict[r].path for r
                      in ctx.config.repo_dict}
        ctx.missing_repo_names_old = ctx.missing_repo_names

        (ctx.config._config, ctx.missing_repo_names) = \
            ctx.config.handler.get_config(repos=repo_paths)

        return ctx.missing_repo_names


class FinishSetupRepos(Command):
    """
        Finalizes the repo setup loop
    """

    def __str__(self):
        return 'finish_setup_repos'

    def execute(self, ctx):
        """ TODO refactor protected-access """
        # now fetch everything with complete config and check out layers
        # except if keep_config is set
        if not ctx.keep_config:
            repos_fetch(ctx.config.get_repos())

            for repo in ctx.config.get_repos():
                repo.checkout()

        logging.debug('Configuration from config file:\n%s',
                      pprint.pformat(ctx.config._config))
