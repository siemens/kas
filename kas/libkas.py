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
    This module contains the core implementation of kas.
"""

import re
import os
import sys
import logging
import tempfile
import asyncio
import errno
import pathlib
import signal
from subprocess import Popen, PIPE
from .context import get_context

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


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
            This method is called when a line is received over stdout.
        """
        if self.live:
            logging.info(line.strip())
        self.stdout.append(line)

    def log_stderr(self, line):
        """
            This method is called when a line is received over stderr.
        """
        if self.live:
            logging.error(line.strip())
        self.stderr.append(line)


async def _read_stream(stream, callback):
    """
        This asynchronous method reads from the output stream of the
        application and transfers each line to the callback function.
    """
    while True:
        line = await stream.readline()
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError as err:
            logging.warning('Could not decode line from stream, ignoring: %s',
                            err)
        if line:
            callback(line)
        else:
            break


async def run_cmd_async(cmd, cwd, env=None, fail=True, liveupdate=True):
    """
        Run a command asynchronously.
    """

    env = env or get_context().environ
    cmdstr = ' '.join(cmd)
    logging.info('%s$ %s', cwd, cmdstr)

    logo = LogOutput(liveupdate)

    try:
        orig_fd = signal.set_wakeup_fd(-1, warn_on_full_buffer=False)
        signal.set_wakeup_fd(orig_fd, warn_on_full_buffer=False)
    except TypeError:
        # Python < 3.7 - we tried our best
        pass

    try:
        process = await asyncio.create_subprocess_exec(
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

    tasks = [
        asyncio.ensure_future(_read_stream(process.stdout, logo.log_stdout)),
        asyncio.ensure_future(_read_stream(process.stderr, logo.log_stderr))
    ]
    await asyncio.wait(tasks)
    ret = await process.wait()

    if ret and fail:
        msg = 'Command "{cwd}$ {cmd}" failed'.format(cwd=cwd, cmd=cmdstr)
        if logo.stderr:
            msg += '\n--- Error summary ---\n'
            for line in logo.stderr:
                msg += line
        logging.error(msg)

    return (ret, ''.join(logo.stdout))


def run_cmd(cmd, cwd, env=None, fail=True, liveupdate=True):
    """
        Runs a command synchronously.
    """

    loop = asyncio.get_event_loop()
    (ret, output) = loop.run_until_complete(
        run_cmd_async(cmd, cwd, env, fail, liveupdate))
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


def repos_fetch(repos):
    """
        Fetches the list of repositories to the kas_work_dir.
    """
    if len(repos) == 0:
        return

    tasks = []
    for repo in repos:
        tasks.append(asyncio.ensure_future(repo.fetch_async()))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))

    for task in tasks:
        if task.result():
            sys.exit(task.result())


def repos_apply_patches(repos):
    """
        Applies the patches to the repositories.
    """
    if len(repos) == 0:
        return

    tasks = []
    for repo in repos:
        tasks.append(asyncio.ensure_future(repo.apply_patches_async()))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))

    for task in tasks:
        if task.result():
            sys.exit(task.result())


def get_build_environ(build_system):
    """
        Creates the build environment variables.
    """
    # nasty side effect function: running oe/isar-init-build-env also
    # creates the conf directory

    init_repo = None
    if build_system in ['openembedded', 'oe']:
        scripts = ['oe-init-build-env']
    elif build_system == 'isar':
        scripts = ['isar-init-build-env']
    else:
        scripts = ['oe-init-build-env', 'isar-init-build-env']
    permutations = \
        [(repo, script) for repo in get_context().config.get_repos()
         for script in scripts]
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

    with tempfile.TemporaryDirectory() as temp_dir:
        script = """#!/bin/bash
        set -e
        source %s $1 > /dev/null
        env
        """ % init_script

        get_bb_env_file = pathlib.Path(temp_dir) / "get_bb_env"
        get_bb_env_file.write_text(script)
        get_bb_env_file.chmod(0o775)

        env = {}
        env['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'

        (_, output) = run_cmd([str(get_bb_env_file), get_context().build_dir],
                              cwd=init_repo.path, env=env, liveupdate=False)

    env = {}
    for line in output.splitlines():
        try:
            (key, val) = line.split('=', 1)
            env[key] = val
        except ValueError:
            pass

    conf_env = get_context().config.get_environment()

    env_vars = ['SSTATE_DIR', 'DL_DIR', 'TMPDIR']
    env_vars.extend(conf_env)

    env.update(conf_env)

    if 'BB_ENV_PASSTHROUGH_ADDITIONS' in env:
        passthrough_additions = env['BB_ENV_PASSTHROUGH_ADDITIONS'] + ' ' + \
            ' '.join(env_vars)
        env.update({'BB_ENV_PASSTHROUGH_ADDITIONS': passthrough_additions})
    elif 'BB_ENV_EXTRAWHITE' in env:
        extra_white = env['BB_ENV_EXTRAWHITE'] + ' ' + ' '.join(env_vars)
        env.update({'BB_ENV_EXTRAWHITE': extra_white})

    env_vars.extend(['SSH_AUTH_SOCK',
                     'SHELL', 'TERM',
                     'GIT_PROXY_COMMAND', 'NO_PROXY'])

    for env_var in env_vars:
        if env_var in os.environ:
            env[env_var] = os.environ[env_var]

    return env


def ssh_add_key_file(env, key_path):
    """
        Adds an ssh key file to the ssh-agent
    """
    with open(key_path) as f:
        key = f.read()
        ssh_add_key(env, key)


def ssh_add_key(env, key):
    """
        Adds an ssh key to the ssh-agent
    """
    # The ssh-agent needs the key to end with a newline, otherwise it
    # unhelpfully prompts for a password
    if not key.endswith('\n'):
        key += '\n'

    process = Popen(['ssh-add', '-'], stdin=PIPE, stdout=None,
                    stderr=PIPE, env=env)
    (_, error) = process.communicate(input=str.encode(key))
    if process.returncode and error:
        logging.error('failed to add ssh key: %s', error)


def ssh_cleanup_agent():
    """
        Removes the identities and stops the ssh-agent instance
    """
    env = get_context().environ
    # remove the identities
    process = Popen(['ssh-add', '-D'], env=env)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to delete SSH identities')

    # stop the ssh-agent
    process = Popen(['ssh-agent', '-k'], env=env)
    process.wait()
    if process.returncode != 0:
        logging.error('failed to stop SSH agent')


def ssh_setup_agent(envkeys=None):
    """
        Starts the ssh-agent
    """
    env = get_context().environ
    envkeys = envkeys or ['SSH_PRIVATE_KEY', 'SSH_PRIVATE_KEY_FILE']
    output = os.popen('ssh-agent -s').readlines()
    for line in output:
        matches = re.search(r"(\S+)\=(\S+)\;", line)
        if matches:
            env[matches.group(1)] = matches.group(2)

    found = False
    for envkey in envkeys:
        if envkey == 'SSH_PRIVATE_KEY_FILE':
            key_path = os.environ.get(envkey)
            if key_path:
                found = True
                logging.info("adding SSH key")
                ssh_add_key_file(env, key_path)
        else:
            key = os.environ.get(envkey)
            if key:
                found = True
                logging.info("adding SSH key")
                ssh_add_key(env, key)

    if found is not True:
        warning = "None of the following environment keys were set: " + \
            ", ".join(envkeys)
        logging.warning(warning)


def ssh_no_host_key_check():
    """
        Disables ssh host key check
    """
    home = os.path.expanduser('~')
    ssh_dir = home + '/.ssh'
    if not os.path.exists(ssh_dir):
        os.mkdir(ssh_dir)
    ssh_config = ssh_dir + "/config"
    generated_content = 'Host *\n\tStrictHostKeyChecking no\n\n'
    try:
        with open(ssh_config, 'x') as fds:
            fds.write(generated_content)
    except FileExistsError:
        with open(ssh_config, 'r') as fds:
            content = fds.read()
        if content != generated_content:
            logging.warning("%s already exists, "
                            "not touching it to disable StrictHostKeyChecking",
                            ssh_config)


def setup_parser_common_args(parser):
    parser.add_argument('config',
                        help='Config file, using .config.yaml in KAS_WORK_DIR '
                        'if none is specified',
                        nargs='?')
    parser.add_argument('--skip',
                        help='Skip build steps',
                        default=[])
    parser.add_argument('--force-checkout', action='store_true',
                        help='Always checkout the desired refspec of each '
                        'repository, discarding any local changes')
    parser.add_argument('--update', action='store_true',
                        help='Pull new upstream changes to the desired '
                        'refspec even if it is already checked out locally')
