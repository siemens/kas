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

import argparse
import re
import os
import sys
import logging
import tempfile
import asyncio
import errno
import pathlib
import signal
from subprocess import Popen, PIPE, run as subprocess_run
from .context import get_context
from .kasusererror import KasUserError, CommandExecError

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class InitBuildEnvError(KasUserError):
    """
    Error related to the OE / ISAR environment setup scripts
    """
    pass


class EnvNotValidError(KasUserError):
    """
    The caller environment is not suited for the requested operation
    """
    pass


class TaskExecError(KasUserError):
    """
    Similar to :class:`kas.kasusererror.CommandExecError` but for kas
    internal tasks
    """
    def __init__(self, command, ret_code):
        self.ret_code = ret_code
        super().__init__(f'{command} failed: error code {ret_code}')


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


def _filter_stderr(capture_stderr, ret, out, err=None):
    if capture_stderr:
        return (ret, out, err or '')
    else:
        return (ret, out)


async def run_cmd_async(cmd, cwd, env=None, fail=True, liveupdate=False,
                        capture_stderr=False):
    """
        Run a command asynchronously.
    """

    env = env or get_context().environ
    cmdstr = ' '.join(cmd)
    logging.debug('%s$ %s', cwd, cmdstr)

    logo = LogOutput(liveupdate)

    orig_fd = signal.set_wakeup_fd(-1, warn_on_full_buffer=False)
    signal.set_wakeup_fd(orig_fd, warn_on_full_buffer=False)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=os.setpgrp)
    except FileNotFoundError as ex:
        if fail:
            raise ex
        return _filter_stderr(capture_stderr, errno.ENOENT, str(ex))
    except PermissionError as ex:
        if fail:
            raise ex
        return _filter_stderr(capture_stderr, errno.EPERM, str(ex))

    # Process termination is a complicated thing. We need to ensure that
    # the event-loop ThreadedChildWatcher thread fires before the loop is
    # terminated. The best we can do it to ask the process to terminate
    # (SIGINT) and wait for it. We need to shield the process wait to avoid
    # that it is killed by the cancellation of the task, as we want a
    # controlled termination. Forced terminations can leak an orphaned process.
    # https://github.com/pytest-dev/pytest-asyncio/issues/708#issuecomment-1868488942
    tasks = [
        asyncio.ensure_future(_read_stream(process.stdout, logo.log_stdout)),
        asyncio.ensure_future(_read_stream(process.stderr, logo.log_stderr))
    ]

    try:
        await asyncio.gather(*[asyncio.shield(t) for t in tasks])
        ret = await asyncio.shield(process.wait())
    except asyncio.CancelledError:
        process.terminate()
        logging.debug('Command "%s" cancelled', cmdstr)
        await process.wait()
        raise

    if ret and fail:
        msg = f'Command "{cwd}$ {cmdstr}" failed'
        if logo.stderr:
            msg += '\n--- Error summary ---\n'
            for line in logo.stderr:
                msg += line
        logging.error(msg)
        raise CommandExecError(cmd, ret)

    return _filter_stderr(capture_stderr, ret,
                          ''.join(logo.stdout), ''.join(logo.stderr))


def run_cmd(cmd, cwd, env=None, fail=True, capture_stderr=False):
    """
        Runs a command synchronously.
    """
    env = env or get_context().environ
    cmdstr = ' '.join(cmd)
    logging.debug('%s$ %s', cwd, cmdstr)

    try:
        ret = subprocess_run(cmd, env=env, cwd=cwd, stdout=PIPE, stderr=PIPE)
        if ret.returncode and fail:
            raise CommandExecError(cmd, ret.returncode)
    except FileNotFoundError as ex:
        if fail:
            raise ex
        return _filter_stderr(capture_stderr, errno.ENOENT, str(ex))
    except PermissionError as ex:
        if fail:
            raise ex
        return _filter_stderr(capture_stderr, errno.EPERM, str(ex))
    return _filter_stderr(capture_stderr, ret.returncode,
                          ret.stdout.decode('utf-8'),
                          ret.stderr.decode('utf-8'))


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

        .. note:: termination point of the asyncio event loop.
    """
    if len(repos) == 0:
        return

    tasks = []
    for repo in repos:
        tasks.append(asyncio.ensure_future(repo.fetch_async()))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except CommandExecError as e:
        raise TaskExecError('fetch repos', e.ret_code)


def repos_apply_patches(repos):
    """
        Applies the patches to the repositories.

        .. note:: termination point of the asyncio event loop.
    """
    if len(repos) == 0:
        return

    tasks = []
    for repo in repos:
        tasks.append(asyncio.ensure_future(repo.apply_patches_async()))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except CommandExecError as e:
        raise TaskExecError('apply patches', e.ret_code)


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
                raise InitBuildEnvError(
                    'Multiple init scripts found '
                    f'({repo.name} vs. {init_repo.name}). '
                    'Resolve ambiguity by removing one of the repos')

            init_repo = repo
            init_script = script
    if not init_repo:
        raise InitBuildEnvError('Did not find any init-build-env script')

    with tempfile.TemporaryDirectory() as temp_dir:
        script = f"""#!/bin/bash
        set -e
        source {init_script} $1 > /dev/null
        env
        """

        get_bb_env_file = pathlib.Path(temp_dir) / "get_bb_env"
        get_bb_env_file.write_text(script)
        get_bb_env_file.chmod(0o775)

        env = {}
        env['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'

        (_, output) = run_cmd([str(get_bb_env_file), get_context().build_dir],
                              cwd=init_repo.path, env=env)

    env = {}
    for line in output.splitlines():
        try:
            (key, val) = line.split('=', 1)
            env[key] = val
        except ValueError:
            pass

    conf_env = get_context().config.get_environment()

    env_vars = ['SSTATE_DIR', 'SSTATE_MIRRORS', 'DL_DIR', 'TMPDIR']
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

    # filter out 'None' values
    env = {k: v for (k, v) in env.items() if v is not None}

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
        logging.error('failed to add ssh key: %s', error.decode('utf-8'))


def ssh_cleanup_agent():
    """
        Removes the identities and stops the ssh-agent instance
    """
    ctx = get_context()
    # remove the identities
    (ret, _) = run_cmd(['ssh-add', '-D'], cwd=ctx.kas_work_dir,
                       env=ctx.environ, fail=False)
    if ret != 0:
        logging.error('failed to delete SSH identities')

    # stop the ssh-agent
    (ret, _) = run_cmd(['ssh-agent', '-k'], cwd=ctx.kas_work_dir,
                       env=ctx.environ, fail=False)
    if ret != 0:
        logging.error('failed to stop SSH agent')


def ssh_setup_agent(envkeys=None):
    """
        Starts the ssh-agent
    """
    ctx = get_context()
    env = ctx.environ
    envkeys = envkeys or ['SSH_PRIVATE_KEY', 'SSH_PRIVATE_KEY_FILE']
    (_, output) = run_cmd(['ssh-agent', '-s'], env=env,
                          cwd=ctx.kas_work_dir)
    for line in output.split('\n'):
        matches = re.search(r"(\S+)\=(\S+)\;", line)
        if matches:
            env[matches.group(1)] = matches.group(2)

    found = False
    for envkey in envkeys:
        if envkey == 'SSH_PRIVATE_KEY_FILE':
            key_path = os.environ.get(envkey)
            if key_path:
                found = True
                logging.info(f"adding SSH key from file '{key_path}'")
                ssh_add_key_file(env, key_path)
        else:
            key = os.environ.get(envkey)
            if key:
                found = True
                logging.info("adding SSH key from env-var 'SSH_PRIVATE_KEY'")
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
    from kas.libcmds import Macro

    setup_cmds = [str(s) for (s, _) in Macro().setup_commands]
    parser.add_argument('--skip',
                        help='Skip build steps. To skip more than one step, '
                        'use this argument multiple times.',
                        default=[],
                        action='append',
                        metavar='STEP',
                        choices=setup_cmds)
    parser.add_argument('--force-checkout', action='store_true',
                        help='Always checkout the desired commit/branch/tag '
                        'of each repository, discarding any local changes')
    parser.add_argument('--update', action='store_true',
                        help='Pull new upstream changes to the desired '
                        'branch even if it is already checked out locally')


def setup_parser_config_arg(parser):
    parser.add_argument('config',
                        help='Config file(s), separated by colon. Using '
                        '.config.yaml in KAS_WORK_DIR if none is '
                        'specified.',
                        nargs='?')


def setup_parser_preserve_env_arg(parser):
    parser.add_argument('-E', '--preserve-env',
                        help='Keep current user environment block',
                        action='store_true')


class ExtendConstAction(argparse._AppendConstAction):
    """Add an 'extend_const' action similar to 'append_const'.

    Based on the existing 'append_const' and 'extend' actions.
    """
    def __init__(self, option_strings, dest, const, default=None,
                 required=False, help=None, metavar=None):
        super(argparse._AppendConstAction, self).__init__(
            option_strings=option_strings, dest=dest, nargs=0, const=const,
            default=default, required=required, help=help, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        if items is None:
            items = []

        if isinstance(items, list):
            items = items[:]
        else:
            import copy
            items = copy.copy(items)

        items.extend(self.const)
        setattr(namespace, self.dest, items)


def setup_parser_keep_config_unchanged_arg(parser):
    # Skip the tasks which would change the config of the build
    # environment
    steps = [
        'setup_dir',
        'finish_setup_repos',
        'repos_checkout',
        'repos_apply_patches',
        'write_bbconfig',
    ]
    parser.add_argument('-k', '--keep-config-unchanged',
                        help='Skip steps that change the configuration',
                        action=ExtendConstAction,
                        dest='skip',
                        const=steps)


def run_handle_preserve_env_arg(ctx, os, args, SetupHome):
    if args.preserve_env:
        # Warn if there's any settings that setup_home would apply
        # but are now ignored
        for var in SetupHome.ENV_VARS:
            if var in os.environ:
                logging.warning('Environment variable "%s" ignored '
                                'because user environment is being used',
                                var)

        if not os.isatty(sys.stdout.fileno()):
            raise EnvNotValidError(
                '--preserve-env can only be run from a tty')

        ctx.environ = os.environ.copy()

        logging.warning("Preserving the current environment block may "
                        "have unintended side effects on the build.")
