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
    This module contains the core implementation of kas.
"""

import re
import os
import sys
import logging
import tempfile
import asyncio
import errno
from subprocess import Popen, PIPE

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class LogOutput:
    """
        Handles the log output of executed applications
    """
    def __init__(self, live):
        self.live = live
        self.stdout = []
        self.stderr = []

    def log_stdout(self, line):
        """
            This method is called when a line over stdout is received.
        """
        if self.live:
            logging.info(line.strip())
        self.stdout.append(line)

    def log_stderr(self, line):
        """
            This method is called when a line over stderr is received.
        """
        if self.live:
            logging.error(line.strip())
        self.stderr.append(line)


@asyncio.coroutine
def _read_stream(stream, callback):
    """
        This asynchronous method reads from the output stream of the
        application and transfers each line to the callback function.
    """
    while True:
        line = yield from stream.readline()
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError as err:
            logging.warning('Could not decode line from stream, ignore it: %s',
                            err)
        if line:
            callback(line)
        else:
            break


@asyncio.coroutine
def run_cmd_async(cmd, cwd, env=None, fail=True, shell=False, liveupdate=True):
    """
        Run a command asynchronously.
    """
    # pylint: disable=too-many-arguments

    env = env or {}
    cmdstr = cmd
    if not shell:
        cmdstr = ' '.join(cmd)
    logging.info('%s$ %s', cwd, cmdstr)

    logo = LogOutput(liveupdate)

    try:
        if shell:
            process = yield from asyncio.create_subprocess_shell(
                cmd,
                env=env,
                cwd=cwd,
                universal_newlines=True,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        else:
            process = yield from asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError as ex:
        if fail:
            raise ex
        return (errno.ENOENT, str(ex))
    except PermissionError as ex:
        if fail:
            raise ex
        return (errno.EPERM, str(ex))

    yield from asyncio.wait([
        _read_stream(process.stdout, logo.log_stdout),
        _read_stream(process.stderr, logo.log_stderr)
    ])
    ret = yield from process.wait()

    if ret and fail:
        msg = 'Command "{cwd}$ {cmd}" failed'.format(cwd=cwd, cmd=cmdstr)
        if logo.stderr:
            msg += '\n--- Error summary ---\n'
            for line in logo.stderr:
                msg += line
        logging.error(msg)

    return (ret, ''.join(logo.stdout))


def run_cmd(cmd, cwd, env=None, fail=True, shell=False, liveupdate=True):
    """
        Runs a command synchronously.
    """
    # pylint: disable=too-many-arguments

    loop = asyncio.get_event_loop()
    (ret, output) = loop.run_until_complete(
        run_cmd_async(cmd, cwd, env, fail, shell, liveupdate))
    if ret and fail:
        sys.exit(ret)
    return (ret, output)


def find_program(paths, name):
    """
        Find a file within the paths array and returns its path.
    """
    for path in paths.split(os.pathsep):
        prg = os.path.join(path, name)
        if os.path.isfile(prg):
            return prg
    return None


def repos_fetch(config, repos):
    """
        Fetches the list of repositories to the kas_work_dir.
    """
    tasks = []
    for repo in repos:
        if not hasattr(asyncio, 'ensure_future'):
            # pylint: disable=no-member,deprecated-method
            task = asyncio.async(repo.fetch_async(config))
        else:
            task = asyncio.ensure_future(repo.fetch_async(config))
        tasks.append(task)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))

    for task in tasks:
        if task.result():
            sys.exit(task.result())


def get_build_environ(config, build_dir):
    """
        Create the build environment variables.
    """
    # pylint: disable=too-many-locals
    # nasty side effect function: running oe/isar-init-build-env also
    # creates the conf directory

    init_repo = None
    permutations = \
        [(repo, script) for repo in config.get_repos()
         for script in ['oe-init-build-env', 'isar-init-build-env']]
    for (repo, script) in permutations:
        if os.path.exists(repo.path + '/' + script):
            if init_repo:
                logging.error('Multiple init scripts found (%s vs. %s). ',
                              repo.name, init_repo.name)
                logging.error('Resolve ambiguity by removing one of the repos')
                sys.exit(1)
            init_repo = repo
            init_script = script
    if not init_repo:
        logging.error('Did not find any init-build-env script')
        sys.exit(1)

    get_bb_env_file = tempfile.mktemp()
    with open(get_bb_env_file, 'w') as fds:
        script = """#!/bin/bash
        set -e
        source %s $1 > /dev/null
        env
        """ % init_script
        fds.write(script)
    os.chmod(get_bb_env_file, 0o775)

    env = {}
    env['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'

    (_, output) = run_cmd([get_bb_env_file, build_dir],
                          cwd=init_repo.path, env=env, liveupdate=False)

    os.remove(get_bb_env_file)

    env = {}
    for line in output.splitlines():
        try:
            (key, val) = line.split('=', 1)
            env[key] = val
        except ValueError:
            pass

    conf_env = config.get_environment()

    env_vars = ['SSTATE_DIR', 'DL_DIR', 'TMPDIR']
    env_vars.extend(conf_env)

    env.update(conf_env)

    if 'BB_ENV_EXTRAWHITE' in env:
        extra_white = env['BB_ENV_EXTRAWHITE'] + ' ' + ' '.join(env_vars)
        env.update({'BB_ENV_EXTRAWHITE': extra_white})

    env_vars.extend(['SSH_AGENT_PID', 'SSH_AUTH_SOCK',
                     'SHELL', 'TERM',
                     'GIT_PROXY_COMMAND', 'NO_PROXY'])

    for env_var in env_vars:
        if env_var in os.environ:
            env[env_var] = os.environ[env_var]

    return env


def ssh_add_key(env, key):
    """
        Add ssh key to the ssh-agent
    """
    process = Popen(['ssh-add', '-'], stdin=PIPE, stdout=None,
                    stderr=PIPE, env=env)
    (_, error) = process.communicate(input=str.encode(key))
    if process.returncode and error:
        logging.error('failed to add ssh key: %s', error)


def ssh_cleanup_agent(config):
    """
        Removes the identities and stop the ssh-agent instance
    """
    # remove the identities
    process = Popen(['ssh-add', '-D'], env=config.environ)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to delete SSH identities')

    # stop the ssh-agent
    process = Popen(['ssh-agent', '-k'], env=config.environ)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to stop SSH agent')


def ssh_setup_agent(config, envkeys=None):
    """
        Starts the ssh-agent
    """
    envkeys = envkeys or ['SSH_PRIVATE_KEY']
    output = os.popen('ssh-agent -s').readlines()
    for line in output:
        matches = re.search(r"(\S+)\=(\S+)\;", line)
        if matches:
            config.environ[matches.group(1)] = matches.group(2)

    for envkey in envkeys:
        key = os.environ.get(envkey)
        if key:
            ssh_add_key(config.environ, key)
        else:
            logging.warning('%s is missing', envkey)


def ssh_no_host_key_check(_):
    """
        Disables ssh host key check
    """
    home = os.path.expanduser('~')
    if not os.path.exists(home + '/.ssh'):
        os.mkdir(home + '/.ssh')
    with open(home + '/.ssh/config', 'w') as fds:
        fds.write('Host *\n\tStrictHostKeyChecking no\n\n')


def kasplugin(plugin_class):
    """
        A decorator that registeres kas plugins
    """
    if not hasattr(kasplugin, 'plugins'):
        setattr(kasplugin, 'plugins', [])
    getattr(kasplugin, 'plugins').append(plugin_class)
