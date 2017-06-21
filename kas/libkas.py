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
    def __init__(self, live):
        self.live = live
        self.stdout = []
        self.stderr = []

    def log_stdout(self, line):
        if self.live:
            logging.info(line.strip())
        self.stdout.append(line)

    def log_stderr(self, line):
        if self.live:
            logging.error(line.strip())
        self.stderr.append(line)


@asyncio.coroutine
def _read_stream(stream, cb):
    while True:
        line = yield from stream.readline()
        try:
            line = line.decode('utf-8')
        except:
            logging.warning('Could not decode line from stream - ignore it')
        if line:
            cb(line)
        else:
            break


@asyncio.coroutine
def _stream_subprocess(cmd, cwd, env, shell, stdout_cb, stderr_cb):
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


def run_cmd(cmd, cwd, env={}, fail=True, shell=False, liveupdate=True):
    rc = 0
    stdout = []
    stderr = []
    cmdstr = cmd
    if not shell:
        cmdstr = ' '.join(cmd)
    logging.info('{}$ {}'.format(cwd, cmdstr))

    logo = LogOutput(liveupdate)
    if asyncio.get_event_loop().is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    rc = loop.run_until_complete(
        _stream_subprocess(cmd, cwd, env, shell,
                           logo.log_stdout, logo.log_stderr))
    loop.close()

    if rc and fail:
        msg = 'Command "{cwd}$ {cmd}" failed\n'.format(cwd=cwd, cmd=cmdstr)
        for line in logo.stderr:
            msg += line
        logging.error(msg)
        sys.exit(rc)

    return (rc, ''.join(logo.stdout))


def find_program(paths, name):
    for path in paths.split(os.pathsep):
        prg = os.path.join(path, name)
        if os.path.isfile(prg):
            return prg
    return None


def get_oe_environ(config, build_dir):
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
    with open(get_bb_env_file, 'w') as f:
        script = """#!/bin/bash
        source oe-init-build-env $1 > /dev/null 2>&1
        env
        """
        f.write(script)
    os.chmod(get_bb_env_file, 0o775)

    env = {}
    env['PATH'] = '/bin:/usr/bin'

    (rc, output) = run_cmd([get_bb_env_file, build_dir],
                           cwd=oe_path, env=env, liveupdate=False)

    os.remove(get_bb_env_file)

    env = {}
    for line in output.splitlines():
        try:
            (key, val) = line.split('=', 1)
            env[key] = val
        except:
            pass

    vars = ['SSTATE_DIR', 'DL_DIR', 'TMPDIR']
    if 'BB_ENV_EXTRAWHITE' in env:
        ew = env['BB_ENV_EXTRAWHITE'] + ' '.join(vars)
        env.update({'BB_ENV_EXTRAWHITE': ew})

    vars.extend(['SSH_AGENT_PID', 'SSH_AUTH_SOCK',
                 'SHELL', 'TERM'])

    for v in vars:
        if v in os.environ:
            env[v] = os.environ[v]

    return env


def ssh_add_key(env, key):
    p = Popen(['/usr/bin/ssh-add', '-'], stdin=PIPE, stdout=None,
              stderr=PIPE, env=env)
    error = p.communicate(input=str.encode(key))[1]
    if p.returncode and error:
        logging.error('failed to add ssh key: {}'.format(error))


def ssh_cleanup_agent(config):
    """Removes the identities and stop the ssh-agent instance """
    # remove the identities
    p = Popen(['/usr/bin/ssh-add', '-D'], env=config.environ)
    p.wait()
    if p.returncode != 0:
        logging.error('failed to delete SSH identities')

    # stop the ssh-agent
    p = Popen(['/usr/bin/ssh-agent', '-k'], env=config.environ)
    p.wait()
    if p.returncode != 0:
        logging.error('failed to stop SSH agent')


def ssh_setup_agent(config, envkeys=['SSH_PRIVATE_KEY']):
    output = os.popen('/usr/bin/ssh-agent -s').readlines()
    for line in output:
        matches = re.search("(\S+)\=(\S+)\;", line)
        if matches:
            config.environ[matches.group(1)] = matches.group(2)

    for ek in envkeys:
        key = os.environ.get(ek)
        if key:
            ssh_add_key(config.environ, key)
        else:
            logging.warning('{} is missing'.format(ek))


def ssh_no_host_key_check(config):
    home = os.path.expanduser('~')
    if not os.path.exists(home + '/.ssh'):
        os.mkdir(home + '/.ssh')
    with open(home + '/.ssh/config', 'w') as f:
        f.write('Host *\n\tStrictHostKeyChecking no\n\n')
