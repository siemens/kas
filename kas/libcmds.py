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

import tempfile
import logging
import shutil
import os
from urllib.parse import urlparse
from .libkas import (ssh_cleanup_agent, ssh_setup_agent, ssh_no_host_key_check,
                     run_cmd, get_oe_environ)

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Macro:
    def __init__(self):
        self.commands = []

    def add(self, command):
        self.commands.append(command)

    def run(self, config, skip=[]):
        for c in self.commands:
            name = str(c)
            if name in skip:
                continue
            pre = config.pre_hook(name)
            if pre:
                logging.debug('execute ' + pre)
                pre(config)
            cmd = config.get_hook(name)
            if cmd:
                logging.debug('execute ' + cmd)
                cmd(config)
            else:
                logging.debug('execute ' + str(c))
                c.execute(config)
            post = config.post_hook(name)
            if post:
                logging.debug('execute ' + post)
                post(config)


class Command:
    def execute(self, config):
        pass


class SetupHome(Command):
    def __init__(self):
        self.tmpdirname = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self.tmpdirname)

    def __str__(self):
        return 'setup_home'

    def execute(self, config):
        with open(self.tmpdirname + '/.wgetrc', 'w') as f:
            f.write('\n')
        with open(self.tmpdirname + '/.netrc', 'w') as f:
            f.write('\n')
        config.environ['HOME'] = self.tmpdirname


class SetupDir(Command):
    def __str__(self):
        return 'setup_dir'

    def execute(self, config):
        os.chdir(config.kas_work_dir)
        if not os.path.exists(config.build_dir):
            os.mkdir(config.build_dir)


class SetupSSHAgent(Command):
    def __str__(self):
        return 'setup_ssh_agent'

    def execute(self, config):
        ssh_setup_agent(config)
        ssh_no_host_key_check(config)


class CleanupSSHAgent(Command):
    """Remove all the identities and stop the ssh-agent instance"""

    def __str__(self):
        return 'cleanup_ssh_agent'

    def execute(self, config):
        ssh_cleanup_agent(config)


class SetupProxy(Command):
    def __str__(self):
        return 'setup_proxy'

    def execute(self, config):
        config.environ.update(config.get_proxy_config())


class SetupEnviron(Command):
    def __str__(self):
        return 'setup_environ'

    def execute(self, config):
        config.environ.update(get_oe_environ(config, config.build_dir))


class WriteConfig(Command):
    def __str__(self):
        return 'write_config'

    def execute(self, config):
        self._write_bblayers_conf(config)
        self._write_local_conf(config)

    def _append_layers(self, config, file):
        for repo in config.get_repos():
            file.write(' \\\n'.join(repo.layers + ['']))

    def _write_bblayers_conf(self, config):
        filename = config.build_dir + '/conf/bblayers.conf'
        with open(filename, 'w') as file:
            file.write(config.get_bblayers_conf_header())
            file.write('BBLAYERS ?= " \\\n')
            self._append_layers(config, file)
            file.write('"\n')

    def _write_local_conf(self, config):
        filename = config.build_dir + '/conf/local.conf'
        with open(filename, 'w') as file:
            file.write(config.get_local_conf_header())
            file.write('MACHINE ?= "{}"\n'.format(config.get_machine()))
            file.write('DISTRO ?= "{}"\n'.format(config.get_distro()))


class ReposFetch(Command):
    def __str__(self):
        return 'repos_fetch'

    def execute(self, config):
        for repo in config.get_repos():
            if repo.git_operation_disabled:
                continue

            if not os.path.exists(repo.path):
                os.makedirs(os.path.dirname(repo.path), exist_ok=True)
                gitsrcdir = os.path.join(config.get_repo_ref_dir() or '',
                                         repo.qualified_name)
                logging.debug('Looking for repo ref dir in {}'.
                              format(gitsrcdir))
                if config.get_repo_ref_dir() and os.path.exists(gitsrcdir):
                    run_cmd(['/usr/bin/git',
                             'clone',
                             '--reference', gitsrcdir,
                             repo.url, repo.path],
                            env=config.environ,
                            cwd=config.kas_work_dir)
                else:
                    run_cmd(['/usr/bin/git', 'clone', '-q', repo.url,
                             repo.path],
                            env=config.environ,
                            cwd=config.kas_work_dir)
                continue

            # Does refspec in the current repository?
            (rc, output) = run_cmd(['/usr/bin/git', 'cat-file',
                                    '-t', repo.refspec], env=config.environ,
                                   cwd=repo.path, fail=False)
            if rc == 0:
                continue

            # No it is missing, try to fetch
            (rc, output) = run_cmd(['/usr/bin/git', 'fetch', '--all'],
                                   env=config.environ,
                                   cwd=repo.path, fail=False)
            if rc:
                logging.warning('Could not update repository {}: {}'.
                                format(repo.name, output))


class ReposCheckout(Command):
    def __str__(self):
        return 'repos_checkout'

    def execute(self, config):
        for repo in config.get_repos():
            if repo.git_operation_disabled:
                continue

            # Check if repos is dirty
            (rc, output) = run_cmd(['/usr/bin/git', 'diff', '--shortstat'],
                                   env=config.environ, cwd=repo.path,
                                   fail=False)
            if len(output):
                logging.warning('Repo {} is dirty. no checkout'.
                                format(repo.name))
                continue

            # Check if current HEAD is what in the config file is defined.
            (rc, output) = run_cmd(['/usr/bin/git', 'rev-parse',
                                    '--verify', 'HEAD'], env=config.environ,
                                   cwd=repo.path)

            if output.strip() == repo.refspec:
                logging.info(('Repo {} has already checkout out correct '
                              'refspec. nothing to do').format(repo.name))
                continue

            run_cmd(['/usr/bin/git', 'checkout', '-q',
                     '{refspec}'.format(refspec=repo.refspec)],
                    cwd=repo.path)
