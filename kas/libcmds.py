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
import sys
import pprint
import configparser
import json
import base64
from git.config import GitConfigParser
from .libkas import (ssh_cleanup_agent, ssh_setup_agent, ssh_no_host_key_check,
                     get_build_environ, repos_fetch, repos_apply_patches)
from .context import ManagedEnvironment as ME
from .context import get_context
from .includehandler import IncludeException
from .kasusererror import ArgsCombinationError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'

KAS_USER_NAME = 'kas User'
KAS_USER_EMAIL = 'kas@example.com'
HTTPS_PORT_DEFAULT = 443
SSH_PORT_DEFAULT = 22


class Macro:
    """
        Contains commands and provides method to run them.
    """

    def __init__(self, use_common_setup=True):
        if use_common_setup:
            repo_loop = Loop('repo_setup_loop')
            repo_loop.add(SetupReposStep())

            # setup commands are pairs of setup / cleanup commands
            self.setup_commands = [
                (SetupDir(), None)
            ]

            if ('SSH_PRIVATE_KEY' in os.environ
                    or 'SSH_PRIVATE_KEY_FILE' in os.environ):
                if 'SSH_AUTH_SOCK' in os.environ:
                    raise ArgsCombinationError(
                        'Internal SSH agent (e.g. for "SSH_PRIVATE_KEY") can '
                        'only be started if no external one is passed.')
                self.setup_commands.append((SetupSSHAgent(),
                                            CleanupSSHAgent()))

            self.setup_commands += [(x, None) for x in [
                SetupHome(),
                InitSetupRepos(),
                repo_loop,
                FinishSetupRepos(),
                ReposCheckout(),
                ReposApplyPatches(),
                SetupEnviron(),
                WriteBBConfig(),
            ]]
        else:
            self.setup_commands = []

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
        def _run_single(command):
            command_name = str(command)
            if command_name in (skip or []):
                return False
            logging.debug('execute %s', command_name)
            command.execute(ctx)
            return True

        cleanup_commands = []
        try:
            for cmd in self.setup_commands:
                if _run_single(cmd[0]) and cmd[1]:
                    cleanup_commands.insert(0, cmd[1])
            for cmd in self.commands:
                _run_single(cmd)
        finally:
            for cmd in cleanup_commands:
                _run_single(cmd)


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
        'REGISTRY_AUTH_FILE',
    ]

    def __init__(self):
        super().__init__()
        self.tmpdirname = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdirname)

    def __str__(self):
        return 'setup_home'

    @staticmethod
    def _ssh_config_present():
        """
            Checks if the .ssh/config file exists or any manual ssh config
            option is set.
        """
        ssh_vars = ['SSH_PRIVATE_KEY', 'SSH_PRIVATE_KEY_FILE', 'SSH_AUTH_SOCK']
        if any(e in os.environ for e in ssh_vars):
            return True

        ssh_path = os.path.expanduser('~/.ssh')
        if os.path.exists(os.path.join(ssh_path, 'config')):
            return True
        return False

    def _setup_netrc(self):
        if os.environ.get('NETRC_FILE', False):
            shutil.copy(os.environ['NETRC_FILE'],
                        self.tmpdirname + "/.netrc")
        if os.environ.get('CI_SERVER_HOST', False) \
                and os.environ.get('CI_JOB_TOKEN', False):
            with open(self.tmpdirname + '/.netrc', 'a') as fds:
                fds.write('machine ' + os.environ['CI_SERVER_HOST'] + '\n'
                          'login gitlab-ci-token\n'
                          'password ' + os.environ['CI_JOB_TOKEN'] + '\n')

    def _setup_registry_auth(self):
        os.makedirs(self.tmpdirname + "/.docker")
        if os.environ.get('REGISTRY_AUTH_FILE', False):
            shutil.copy(os.environ['REGISTRY_AUTH_FILE'],
                        self.tmpdirname + "/.docker/config.json")
        elif not os.path.exists(self.tmpdirname + '/.docker/config.json'):
            with open(self.tmpdirname + '/.docker/config.json', 'w') as fds:
                fds.write("{}")

        if os.environ.get('CI_REGISTRY', False) \
                and os.environ.get('CI_JOB_TOKEN', False) \
                and os.environ.get('CI_REGISTRY_USER', False):
            with open(self.tmpdirname + '/.docker/config.json', 'r+') as fds:
                data = json.loads(fds.read())
                token = os.environ['CI_JOB_TOKEN']
                base64_token = base64.b64encode(token.encode()).decode()
                auths = data.get('auths', {})
                auths.update(
                    {os.environ['CI_REGISTRY']: {"auth": base64_token}})
                data['auths'] = auths
                fds.seek(0)
                fds.write(json.dumps(data, indent=4))
                fds.truncate()

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

    @staticmethod
    def _setup_gitlab_ci_ssh_rewrite(config):
        ci_host = os.environ.get('CI_SERVER_HOST', None)
        ci_port = os.environ.get('CI_SERVER_PORT', HTTPS_PORT_DEFAULT)
        ci_prot = os.environ.get('CI_SERVER_PROTOCOL', 'https')
        # added in GitLab 15.11. Set sensible defaults for older versions.
        ci_ssh_host = os.environ.get('CI_SERVER_SHELL_SSH_HOST', ci_host)
        ci_ssh_port = os.environ.get('CI_SERVER_SHELL_SSH_PORT',
                                     SSH_PORT_DEFAULT)

        for host in [ci_host, f'{ci_host}:{ci_port}']:
            section = f'url "{ci_prot}://{host}/"'
            config.add_value(section, 'insteadOf',
                             f'git@{ci_ssh_host}:')
            config.add_value(section, 'insteadOf',
                             f'git@{ci_ssh_host}:{ci_ssh_port}')
            config.add_value(section, 'insteadOf',
                             f'ssh://git@{ci_ssh_host}/')
            config.add_value(section, 'insteadOf',
                             f'ssh://git@{ci_ssh_host}:{ci_ssh_port}/')

    def _setup_gitconfig(self):
        gitconfig_host = os.environ.get('GITCONFIG_FILE', False)
        gitconfig_kas = self.tmpdirname + '/.gitconfig'

        # when running in a externally managed environment,
        # always try to read the gitconfig
        if not gitconfig_host and get_context().managed_env:
            gitconfig_host = os.path.expanduser('~/.gitconfig')

        if gitconfig_host and os.path.exists(gitconfig_host):
            shutil.copy(gitconfig_host, gitconfig_kas)

        with GitConfigParser(gitconfig_kas, read_only=False) as config:
            if os.environ.get('GIT_CREDENTIAL_HELPER', False):
                config['credential'] = {
                    'helper': os.environ.get('GIT_CREDENTIAL_HELPER')
                }
                if os.environ.get('GIT_CREDENTIAL_USEHTTPPATH', False):
                    config['credential']['useHttpPath'] = \
                        os.environ.get('GIT_CREDENTIAL_USEHTTPPATH')
            # in GitLab CI, add ssh -> https rewrites if no config is present
            ci_server = os.environ.get('CI_SERVER_HOST', None)
            if get_context().managed_env == ME.GITLAB_CI and ci_server and \
                    not self._ssh_config_present() and \
                    not os.path.exists(gitconfig_host):
                logging.debug('Adding GitLab CI ssh -> https rewrites')
                self._setup_gitlab_ci_ssh_rewrite(config)
            config.write()

    def execute(self, ctx):
        managed_env = get_context().managed_env
        if managed_env:
            logging.info(f'Running on {managed_env}')
        def_umask = os.umask(0o077)
        self._setup_netrc()
        self._setup_registry_auth()
        self._setup_gitconfig()
        self._setup_aws_creds()
        os.umask(def_umask)

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
                          [_get_layer_path_under_topdir(ctx, layer)
                           for repo in sorted(ctx.config.get_repos(),
                                              key=lambda r: r.name)
                           for layer in sorted(repo.layers)]))
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

    def _vcs_operate_as_kas(self, gitconfig):
        # currently only implemented for git
        with GitConfigParser(gitconfig, read_only=False) as config:
            # in case no user is defined, we keep the kas user
            user_orig = {
                'name': config.get('user', 'name',
                                   fallback=KAS_USER_NAME),
                'email': config.get('user', 'email',
                                    fallback=KAS_USER_EMAIL)
            }
            config.set_value('user', 'name', KAS_USER_NAME)
            config.set_value('user', 'email', KAS_USER_EMAIL)
            config.write()
            return user_orig

    def _vcs_restore_user(self, gitconfig, user):
        # currently only implemented for git
        with GitConfigParser(gitconfig, read_only=False) as config:
            config['user'] = user
            config.write()

    def execute(self, ctx):
        if 'HOME' not in ctx.environ:
            raise ArgsCombinationError('Apply patches requires setup_home')

        gitconfig = ctx.environ['HOME'] + '/.gitconfig'
        user = self._vcs_operate_as_kas(gitconfig)

        repos_apply_patches(ctx.config.get_repos())

        self._vcs_restore_user(gitconfig, user)


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
            ctx.missing_repos.append((repo_name,
                                      ctx.config.get_repo(repo_name)))

        repos_fetch([v for k, v in ctx.missing_repos])

        for _, repo in ctx.missing_repos:
            repo.checkout()

        ctx.config.repo_dict.update(
            {id: repo for id, repo in ctx.missing_repos})

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

        if sys.version_info < (3, 8):
            config_str = pprint.pformat(ctx.config.get_config())
        else:
            config_str = pprint.pformat(ctx.config.get_config(),
                                        sort_dicts=False)
        logging.debug('Configuration from config file:\n%s', config_str)


class ReposCheckout(Command):
    """
        Ensures that the right revision of each repo is checked out.
    """

    def __str__(self):
        return 'repos_checkout'

    def execute(self, ctx):
        for repo in ctx.config.get_repos():
            repo.checkout()
