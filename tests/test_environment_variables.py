# kas - setup tool for bitbake based projects
#
# Copyright (c) Peter Hatina, 2021
# Copyright (c) Siemens AG, 2021-2022
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

import os
import shutil
import pathlib
import subprocess
import re
import pytest
from kas import kas
from kas.context import create_global_context
from kas.kasusererror import ArgsCombinationError


def test_build_dir_is_placed_inside_work_dir_by_default(monkeykas, tmpdir):
    conf_dir = str(tmpdir / 'test_env_variables')
    shutil.copytree('tests/test_environment_variables', conf_dir)

    monkeykas.chdir(conf_dir)

    kas.kas(['checkout', 'test.yml'])

    assert os.path.exists(os.path.join(os.getcwd(), 'build', 'conf'))


def test_build_dir_can_be_specified_by_environment_variable(monkeykas, tmpdir):
    conf_dir = str(tmpdir / 'test_env_variables')
    build_dir = str(tmpdir / 'test_build_dir')
    shutil.copytree('tests/test_environment_variables', conf_dir)
    monkeykas.chdir(conf_dir)

    monkeykas.setenv('KAS_BUILD_DIR', build_dir)
    kas.kas(['checkout', 'test.yml'])

    assert os.path.exists(os.path.join(build_dir, 'conf'))


def test_ssh_agent_setup(monkeykas, tmpdir, capsys):
    conf_dir = str(tmpdir / 'test_ssh_agent_setup')
    shutil.copytree('tests/test_environment_variables', conf_dir)
    monkeykas.chdir(conf_dir)

    SSH_AUTH_SOCK = '/tmp/ssh-KLTafE/agent.64708'

    with monkeykas.context() as mp:
        envfile = tmpdir / 'env'
        mp.setenv('SSH_AUTH_SOCK', SSH_AUTH_SOCK)
        kas.kas(['shell', '-c', f'env > {envfile}', 'test.yml'])
        env = _get_env_from_file(envfile)
        assert env['SSH_AUTH_SOCK'] == SSH_AUTH_SOCK

    with monkeykas.context() as mp:
        mp.setenv('SSH_AUTH_SOCK', SSH_AUTH_SOCK)
        mp.setenv('SSH_PRIVATE_KEY', 'id_rsa')
        with pytest.raises(ArgsCombinationError):
            kas.kas(['checkout', 'test.yml'])

    privkey_file = f'{tmpdir}/id_ecdsa_test'
    genkey_cmd = ['ssh-keygen', '-f', privkey_file, '-N', '', '-t', 'ecdsa']
    subprocess.check_call(genkey_cmd)
    # ensure we also get the info messages
    log = kas.logging.getLogger()
    log.setLevel(kas.logging.INFO)
    # flush the captured output
    capsys.readouterr()
    with monkeykas.context() as mp:
        mp.setenv('SSH_PRIVATE_KEY_FILE', privkey_file)
        kas.kas(['checkout', 'test.yml'])
        out = capsys.readouterr().err
        assert 'adding SSH key from file' in out
        assert 'ERROR' not in out

    with monkeykas.context() as mp:
        privkey = pathlib.Path(privkey_file).read_text()
        mp.setenv('SSH_PRIVATE_KEY', privkey)
        kas.kas(['checkout', 'test.yml'])
        out = capsys.readouterr().err
        assert 'adding SSH key from env-var' in out
        assert 'ERROR' not in out


def _get_env_from_file(filename):
    env = {}
    with filename.open() as f:
        for line in f.readlines():
            key, val = line.split("=", 1)
            env[key] = val.strip()
    return env


def _test_env_section_export(monkeykas, tmpdir, bb_env_var, bb_repo):
    conf_dir = pathlib.Path(str(tmpdir / 'test_env_variables'))
    env_out = conf_dir / 'env_out'
    bb_env_out = conf_dir / 'bb_env_out'
    init_build_env = conf_dir / 'oe-init-build-env'

    shutil.copytree('tests/test_environment_variables', str(conf_dir))
    monkeykas.chdir(conf_dir)
    monkeykas.setenv('KAS_CLONE_DEPTH', '1')
    monkeykas.setenv('KAS_PREMIRRORS', 'https://git\\.openembedded\\.org/ '
                     'https://github.com/openembedded/\n')

    # Overwrite oe-init-build-env script
    # BB_ENV_* filter variables are only exported by
    # kas when they are already exported in the setup environment script
    script = """#!/bin/sh
    export %s="FOO"
    export PATH="%s/%s/bin:${PATH}"
    """ % (bb_env_var, str(conf_dir), bb_repo)
    init_build_env.write_text(script)
    init_build_env.chmod(0o775)

    # Before executing bitbake, first get the bitbake.conf
    kas.kas(['checkout', 'test_env.yml'])
    shutil.copy(str(conf_dir / bb_repo / 'conf' / 'bitbake.conf'),
                str(pathlib.Path('build') / 'conf' / 'bitbake.conf'))

    kas.kas(['shell', '-c', 'env > %s' % env_out, 'test_env.yml'])
    kas.kas(['shell', '-c', 'bitbake -e > %s' % bb_env_out, 'test_env.yml'])

    # Check kas environment
    test_env = _get_env_from_file(env_out)

    # Variables with 'None' assigned should not be added to environment
    try:
        _ = test_env['TESTVAR_WHITELIST']
        assert False
    except KeyError:
        assert True

    assert test_env['TESTVAR_DEFAULT_VAL'] == 'BAR'
    assert 'TESTVAR_WHITELIST' in test_env[bb_env_var]

    # Check bitbake's environment
    test_bb_env = {}
    with bb_env_out.open() as f:
        for line in f.readlines():
            if re.match(r'^#', line):
                continue
            match = re.match(r'(^[a-zA-Z0-9_]+)=\"([a-zA-Z0-9_ ]+)\"', line)
            if match:
                key, val = match.group(1), match.group(2)
                test_bb_env[key] = val.strip()

    assert 'TESTVAR_WHITELIST' in test_bb_env[bb_env_var]
    assert test_bb_env["TESTVAR_DEFAULT_VAL"] == "BAR"


# BB_ENV_EXTRAWHITE is deprecated but may still be used
@pytest.mark.online
def test_env_section_export_bb_extra_white(monkeykas, tmpdir):
    _test_env_section_export(monkeykas, tmpdir, 'BB_ENV_EXTRAWHITE',
                             'bitbake_old')


@pytest.mark.online
def test_env_section_export_bb_env_passthrough_additions(monkeykas, tmpdir):
    _test_env_section_export(monkeykas, tmpdir, 'BB_ENV_PASSTHROUGH_ADDITIONS',
                             'bitbake_new')


def test_managed_env_detection(monkeykas):
    with monkeykas.context() as mp:
        mp.setenv('GITLAB_CI', 'true')
        ctx = create_global_context([])
        me = ctx.managed_env
        assert bool(me)
        assert str(me) == 'GitLab CI'
    with monkeykas.context() as mp:
        mp.setenv('GITHUB_ACTIONS', 'true')
        ctx = create_global_context([])
        me = ctx.managed_env
        assert bool(me)
        assert str(me) == 'GitHub Actions'
    with monkeykas.context() as mp:
        mp.setenv('REMOTE_CONTAINERS', 'true')
        mp.setenv('REMOTE_CONTAINERS_FOO', 'bar')
        ctx = create_global_context([])
        me = ctx.managed_env
        assert bool(me)
        assert str(me) == 'VSCode Remote Containers'
        assert ctx.environ['REMOTE_CONTAINERS_FOO'] == 'bar'
