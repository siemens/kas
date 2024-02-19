# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2020
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
import configparser
from git.config import GitConfigParser
from .libkas import (ssh_cleanup_agent, ssh_setup_agent, ssh_no_host_key_check,
                     get_build_environ, repos_fetch, repos_apply_patches)
from .includehandler import IncludeException
from .kasusererror import ArgsCombinationError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Macro:
    """
        Contains commands and provides method to run them.
    """

    def __init__(self, use_common_setup=True, use_common_cleanup=True):
        if use_common_setup:
            repo_loop = Loop('repo_setup_loop')
            repo_loop.add(SetupReposStep())

            self.setup_commands = [
                SetupDir(),
            ]

            if ('SSH_PRIVATE_KEY' in os.environ
                    or 'SSH_PRIVATE_KEY_FILE' in os.environ):
                if 'SSH_AUTH_SOCK' in os.environ:
                    raise ArgsCombinationError(
                        'Internal SSH agent (e.g. for "SSH_PRIVATE_KEY") can '
                        'only be started if no external one is passed.')
                self.setup_commands.append(SetupSSHAgent())

            self.setup_commands += [
                SetupHome(),
                InitSetupRepos(),
                repo_loop,
                FinishSetupRepos(),
                ReposCheckout(),
                ReposApplyPatches(),
                SetupEnviron(),
                WriteBBConfig(),
            ]
        else:
            self.setup_commands = []

        if (use_common_cleanup
                and ('SSH_PRIVATE_KEY' in os.environ
                     or 'SSH_PRIVATE_KEY_FILE' in os.environ)):
            self.cleanup_commands = [
                CleanupSSHAgent(),
            ]
        else:
            self.cleanup_commands = []

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
        joined_commands = self.setup_commands + \
            self.commands + self.cleanup_commands
        for command in joined_commands:
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

    # A list of environment variables that SETUP_HOME uses
    # This should be kept up to date with any code in execute()
    ENV_VARS = [
        'GIT_CREDENTIAL_HELPER',
        'GIT_CREDENTIAL_USEHTTPPATH',
        'GITCONFIG_FILE',
        'AWS_CONFIG_FILE',
        'AWS_ROLE_ARN',
        'AWS_SHARED_CREDENTIALS_FILE',
        'AWS_WEB_IDENTITY_TOKEN_FILE',
        'NETRC_FILE',
    ]

    def __init__(self):
        super().__init__()
        self.tmpdirname = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdirname)

    def __str__(self):
        return 'setup_home'

    def _setup_aws_creds(self):
        aws_dir = self.tmpdirname + "/.aws"
        conf_file = aws_dir + "/config"
        shared_creds_file = aws_dir + "/credentials"
        os.makedirs(aws_dir)
        if os.environ.get('AWS_CONFIG_FILE') \
                and os.environ.get('AWS_SHARED_CREDENTIALS_FILE'):
            shutil.copy(os.environ['AWS_CONFIG_FILE'], conf_file)
            shutil.copy(os.environ['AWS_SHARED_CREDENTIALS_FILE'],
                        shared_creds_file)

        # OAuth 2.0 workflow credentials
        if os.environ.get('AWS_WEB_IDENTITY_TOKEN_FILE') \
                and os.environ.get('AWS_ROLE_ARN'):
            webid_token_file = aws_dir + '/web_identity_token'
            config = configparser.ConfigParser()
            if os.path.exists(conf_file):
                config.read(conf_file)
            if 'default' not in config:
                config['default'] = {}
            config['default']['role_arn'] = os.environ.get('AWS_ROLE_ARN')
            config['default']['web_identity_token_file'] = webid_token_file
            with open(aws_dir + '/config', 'w') as fds:
                config.write(fds)
            shutil.copy(os.environ['AWS_WEB_IDENTITY_TOKEN_FILE'],
                        webid_token_file)

    def _setup_gitconfig(self):
        gitconfig_host = os.environ.get('GITCONFIG_FILE', False)
        gitconfig_kas = self.tmpdirname + '/.gitconfig'

        # when running in the github ci, always try to read the gitconfig
        if not gitconfig_host and \
           os.environ.get('GITHUB_ACTIONS', False) == 'true':
            gitconfig_host = os.path.expanduser('~/.gitconfig')

        if gitconfig_host and os.path.exists(gitconfig_host):
            shutil.copy(gitconfig_host, gitconfig_kas)

        with GitConfigParser(gitconfig_kas, read_only=False) as config:
            # overwrite user as kas operates git
            config['user'] = {
                'email': 'kas@example.com',
                'name': 'Kas User'
            }
            if os.environ.get('GIT_CREDENTIAL_HELPER', False):
                config['credential'] = {
                    'helper': os.environ.get('GIT_CREDENTIAL_HELPER')
                }
                if os.environ.get('GIT_CREDENTIAL_USEHTTPPATH', False):
                    config['credential']['useHttpPath'] = \
                        os.environ.get('GIT_CREDENTIAL_USEHTTPPATH')
            config.write()

    def execute(self, ctx):
        if os.environ.get('NETRC_FILE', False):
            shutil.copy(os.environ['NETRC_FILE'],
                        self.tmpdirname + "/.netrc")
        if os.environ.get('CI_SERVER_HOST', False) \
                and os.environ.get('CI_JOB_TOKEN', False):
            with open(self.tmpdirname + '/.netrc', 'a') as fds:
                fds.write('\n# appended by kas, you have gitlab CI env\n')
                fds.write('machine ' + os.environ['CI_SERVER_HOST'] + '\n'
                          'login gitlab-ci-token\n'
                          'password ' + os.environ['CI_JOB_TOKEN'] + '\n')

        self._setup_gitconfig()
        self._setup_aws_creds()

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
        ssh_tools = ['ssh', 'ssh-add', 'ssh-agent']
        for tool in ssh_tools:
            if shutil.which(tool) is None:
                raise RuntimeError('SSH setup requested but could '
                                   f'not find "{tool}" in PATH')
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
        ctx.environ.update(get_build_environ(ctx.config.get_build_system()))


class WriteBBConfig(Command):
    """
        Writes bitbake configuration files into the build directory.
    """

    def __str__(self):
        return 'write_bbconfig'

    def execute(self, ctx):
        def _get_layer_path_under_topdir(ctx, layer):
            """
                Returns a path relative to ${TOPDIR}.
                TOPDIR is a BB variable pointing to the build directory.
                It is not expanded by KAS, hence we avoid
                absolute paths pointing into the build host.
            """
            relpath = os.path.relpath(layer, ctx.build_dir)
            return '${TOPDIR}/' + relpath

        def _write_bblayers_conf(ctx):
            filename = ctx.build_dir + '/conf/bblayers.conf'
            if not os.path.isdir(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            with open(filename, 'w') as fds:
                fds.write(ctx.config.get_bblayers_conf_header())
                fds.write('BBLAYERS ?= " \\\n    ')
                fds.write(' \\\n    '.join(
                    sorted(_get_layer_path_under_topdir(ctx, layer)
                           for repo in ctx.config.get_repos()
                           for layer in repo.layers)))
                fds.write('"\n')
                fds.write('BBPATH ?= "${TOPDIR}"\n')
                fds.write('BBFILES ??= ""\n')

        def _write_local_conf(ctx):
            filename = ctx.build_dir + '/conf/local.conf'
            with open(filename, 'w') as fds:
                fds.write(ctx.config.get_local_conf_header())
                fds.write(f'MACHINE ??= "{ctx.config.get_machine()}"\n')
                fds.write(f'DISTRO ??= "{ctx.config.get_distro()}"\n')
                fds.write('BBMULTICONFIG ?= '
                          f'"{ctx.config.get_multiconfig()}"\n')

        _write_bblayers_conf(ctx)
        _write_local_conf(ctx)


class ReposApplyPatches(Command):
    """
        Applies the patches defined in the configuration to the repositories.
    """

    def __str__(self):
        return 'repos_apply_patches'

    def execute(self, ctx):
        repos_apply_patches(ctx.config.get_repos())


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
        if not ctx.missing_repo_names:
            return False

        if ctx.missing_repo_names == ctx.missing_repo_names_old:
            raise IncludeException('Could not fetch all repos needed by '
                                   'includes. Missing repos: {}'
                                   .format(', '.join(ctx.missing_repo_names)))

        logging.debug('Missing repos for complete config:\n%s',
                      pprint.pformat(ctx.missing_repo_names))

        ctx.missing_repos = []
        for repo_name in ctx.missing_repo_names:
            if repo_name not in ctx.config.get_repos_config():
                # we don't have this repo yet (e.g. due to transitive incl.)
                continue
            ctx.missing_repos.append(ctx.config.get_repo(repo_name))

        repos_fetch(ctx.missing_repos)

        for repo in ctx.missing_repos:
            repo.checkout()

        ctx.config.repo_dict.update(
            {repo.name: repo for repo in ctx.missing_repos})

        repo_paths = {r: ctx.config.repo_dict[r].path for r
                      in ctx.config.repo_dict}
        ctx.missing_repo_names_old = ctx.missing_repo_names

        ctx.missing_repo_names = \
            ctx.config.find_missing_repos(repo_paths)

        return ctx.missing_repo_names


class FinishSetupRepos(Command):
    """
        Finalizes the repo setup loop
    """

    def __str__(self):
        return 'finish_setup_repos'

    def execute(self, ctx):
        # now fetch everything with complete config
        repos_fetch(ctx.config.get_repos())

        logging.debug('Configuration from config file:\n%s',
                      pprint.pformat(ctx.config.get_config()))


class ReposCheckout(Command):
    """
        Ensures that the right revision of each repo is checked out.
    """

    def __str__(self):
        return 'repos_checkout'

    def execute(self, ctx):
        for repo in ctx.config.get_repos():
            repo.checkout()
