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
        This asynchronious method reads from the output stream of the
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
def _stream_subprocess(cmd, cwd, env, shell, stdout_cb, stderr_cb):
    """
        This function starts the subprocess, sets up the output stream
        handlers and waits until the process has existed
    """
    # pylint: disable=too-many-arguments

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

    yield from asyncio.wait([
        _read_stream(process.stdout, stdout_cb),
        _read_stream(process.stderr, stderr_cb)
    ])
    ret = yield from process.wait()
    return ret


def run_cmd(cmd, cwd, env=None, fail=True, shell=False, liveupdate=True):
    """
        Starts a command.
    """
    # pylint: disable=too-many-arguments

    env = env or {}
    retc = 0
    cmdstr = cmd
    if not shell:
        cmdstr = ' '.join(cmd)
    logging.info('%s$ %s', cwd, cmdstr)

    logo = LogOutput(liveupdate)
    if asyncio.get_event_loop().is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    retc = loop.run_until_complete(
        _stream_subprocess(cmd, cwd, env, shell,
                           logo.log_stdout, logo.log_stderr))
    loop.close()

    if retc and fail:
        msg = 'Command "{cwd}$ {cmd}" failed\n'.format(cwd=cwd, cmd=cmdstr)
        for line in logo.stderr:
            msg += line
        logging.error(msg)
        sys.exit(retc)

    return (retc, ''.join(logo.stdout))


def find_program(paths, name):
    """
        Find a file within the paths array and returns its path.
    """
    for path in paths.split(os.pathsep):
        prg = os.path.join(path, name)
        if os.path.isfile(prg):
            return prg
    return None


def get_oe_environ(config, build_dir):
    """
        Create the openembedded environment variables.
    """
    # pylint: disable=too-many-locals
    # nasty side effect function: running oe-init-build-env also
    # creates the conf directory

    oe_path = None
    for repo in config.get_repos():
        if os.path.exists(repo.path + '/oe-init-build-env'):
            oe_path = repo.path
            break
    if not oe_path:
        logging.error('Did not find oe-init-build-env')
        sys.exit(1)

    get_bb_env_file = tempfile.mktemp()
    with open(get_bb_env_file, 'w') as fds:
        script = """#!/bin/bash
        source oe-init-build-env $1 > /dev/null 2>&1
        env
        """
        fds.write(script)
    os.chmod(get_bb_env_file, 0o775)

    env = {}
    env['PATH'] = '/bin:/usr/bin'

    (_, output) = run_cmd([get_bb_env_file, build_dir],
                          cwd=oe_path, env=env, liveupdate=False)

    os.remove(get_bb_env_file)

    env = {}
    for line in output.splitlines():
        try:
            (key, val) = line.split('=', 1)
            env[key] = val
        except ValueError:
            pass

    env_vars = ['SSTATE_DIR', 'DL_DIR', 'TMPDIR']
    if 'BB_ENV_EXTRAWHITE' in env:
        extra_white = env['BB_ENV_EXTRAWHITE'] + ' '.join(env_vars)
        env.update({'BB_ENV_EXTRAWHITE': extra_white})

    env_vars.extend(['SSH_AGENT_PID', 'SSH_AUTH_SOCK',
                     'SHELL', 'TERM'])

    for env_var in env_vars:
        if env_var in os.environ:
            env[env_var] = os.environ[env_var]

    return env


def ssh_add_key(env, key):
    """
        Add ssh key to the ssh-agent
    """
    process = Popen(['/usr/bin/ssh-add', '-'], stdin=PIPE, stdout=None,
                    stderr=PIPE, env=env)
    (_, error) = process.communicate(input=str.encode(key))
    if process.returncode and error:
        logging.error('failed to add ssh key: %s', error)


def ssh_cleanup_agent(config):
    """
        Removes the identities and stop the ssh-agent instance
    """
    # remove the identities
    process = Popen(['/usr/bin/ssh-add', '-D'], env=config.environ)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to delete SSH identities')

    # stop the ssh-agent
    process = Popen(['/usr/bin/ssh-agent', '-k'], env=config.environ)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to stop SSH agent')


def ssh_setup_agent(config, envkeys=None):
    """
        Starts the ssh-agent
    """
    envkeys = envkeys or ['SSH_PRIVATE_KEY']
    output = os.popen('/usr/bin/ssh-agent -s').readlines()
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
