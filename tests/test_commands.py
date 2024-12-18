# kas - setup tool for bitbake based projects
#
# Copyright (c) Konsulko Group, 2020
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

import glob
import os
import pathlib
import shutil
import json
import yaml
import subprocess
import pytest
from kas import kas
from kas.libkas import TaskExecError, KasUserError, run_cmd
from kas.attestation import file_digest_slow


@pytest.mark.online
def test_for_all_repos(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['for-all-repos', 'test.yml',
             '''if [ -n "${KAS_REPO_URL}" ]; then git rev-parse HEAD \
                     >> %s/ref_${KAS_REPO_NAME}; fi''' % tdir])

    with open('ref_kas_1.0', 'r') as f:
        assert f.readline().strip() \
            == '907816a5c4094b59a36aec12226e71c461c05b77'
    with open('ref_kas_1.1', 'r') as f:
        assert f.readline().strip() \
            == 'e9ca55a239caa1a2098e1d48773a29ea53c6cab2'


@pytest.mark.online
def test_for_all_repos_keep_config_unchanged(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)

    with pytest.raises(FileNotFoundError, match=r'.*/kas_1.[01]'):
        kas.kas(['for-all-repos', '--keep-config-unchanged', 'test.yml',
                 'pwd'])

    assert not os.path.exists('kas_1.0')
    assert not os.path.exists("kas_1.1")


@pytest.mark.online
def test_checkout(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['checkout', 'test.yml'])

    # Ensure that local.conf and bblayers.conf are populated, check that no
    # build has been executed by ensuring that no tmp, sstate-cache or
    # downloads directories are present.
    assert os.path.exists('build/conf/local.conf')
    assert os.path.exists('build/conf/bblayers.conf')
    assert not glob.glob('build/tmp*')
    assert not os.path.exists('build/downloads')
    assert not os.path.exists('build/sstate-cache')


def test_invalid_checkout(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    with pytest.raises(TaskExecError):
        kas.kas(['checkout', 'test-invalid.yml'])


@pytest.mark.online
def test_checkout_with_ci_rewrite(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    with monkeykas.context() as mp:
        mp.setenv('GITLAB_CI', 'true')
        mp.setenv('CI_SERVER_HOST', 'github.com')
        mp.setenv('CI_JOB_TOKEN', 'not-needed')
        kas.kas(['checkout', 'test-url-rewrite.yml'])


@pytest.mark.online
def test_checkout_create_refs(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    repo_cache = pathlib.Path(str(tmpdir.mkdir('repos')))
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    monkeykas.setenv('KAS_REPO_REF_DIR', str(repo_cache))
    kas.kas(['checkout', 'test.yml'])
    assert os.path.exists(str(repo_cache / 'github.com.siemens.kas.git'))
    assert os.path.exists('kas_1.0/.git/objects/info/alternates')


@pytest.mark.online
def test_checkout_shallow(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)
    with monkeykas.context() as mp:
        mp.setenv('KAS_CLONE_DEPTH', 'invalid')
        with pytest.raises(KasUserError):
            kas.kas(['checkout', 'test-shallow.yml'])

    with monkeykas.context() as mp:
        mp.setenv('KAS_CLONE_DEPTH', '1')
        kas.kas(['checkout', 'test-shallow.yml'])
    for repo in ['kas_1', 'kas_2', 'kas_3', 'kas_4']:
        output = subprocess.check_output(
            ['git', 'rev-list', '--count', 'HEAD'], cwd=repo)
        count = int(output.decode('utf-8').strip())
        if repo == 'kas_4':
            assert count >= 1
        else:
            assert count == 1


@pytest.mark.online
def test_shallow_updates(monkeykas, tmpdir):
    def _get_commit(repo):
        output = subprocess.check_output(
            ['git', 'rev-parse', '--verify', 'HEAD'], cwd=repo)
        return output.decode('utf-8').strip()

    tdir = tmpdir / 'test_commands'
    tdir.mkdir()
    shutil.copy('tests/test_commands/oe-init-build-env', tdir)
    monkeykas.chdir(tdir)
    monkeykas.setenv('KAS_CLONE_DEPTH', '1')
    # test non-pinned checkout of master branch
    base_yml = {'header': {'version': 15}, 'repos': {
                'this': {},
                'kas': {
                    'url': 'https://github.com/siemens/kas.git',
                    'branch': 'master'
                }}}
    with open(tdir / 'kas.yml', 'w') as f:
        yaml.dump(base_yml, f)
    kas.kas(['checkout', 'kas.yml'])
    # switch branches, perform checkout again
    base_yml['repos']['kas']['branch'] = 'next'
    with open(tdir / 'kas.yml', 'w') as f:
        yaml.dump(base_yml, f)
    kas.kas(['checkout', 'kas.yml'])
    # pin commit on next branch
    commit = '5d1ab6e8ed3a12c7093c9041f104fb6a2db701a1'
    base_yml_lock = {'header': {'version': 15},
                     'overrides': {'repos': {'kas': {'commit': commit}}}}
    with open(tdir / 'kas.lock.yml', 'w') as f:
        yaml.dump(base_yml_lock, f)
    kas.kas(['checkout', 'kas.yml'])
    assert _get_commit('kas') == commit
    # update to latest revision of next branch
    kas.kas(['checkout', '--update', 'kas.yml'])
    assert _get_commit('kas') != commit


@pytest.mark.online
def test_repo_includes(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_repo_includes', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['checkout', 'test.yml'])


@pytest.mark.online
def test_dump(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_repo_includes', tdir)
    monkeykas.chdir(tdir)

    formats = ['json', 'yaml']
    resolve = ['', '--resolve-refs', '--resolve-env']
    # test cross-product of these options (formats x resolve)
    for f, r in ((f, r) for f in formats for r in resolve):
        outfile = 'test_flat%s.%s' % (r, f)

        with monkeykas.context() as mp:
            if r == '--resolve-env':
                mp.setenv('TESTVAR_FOO', 'KAS')
            kas.kas(('dump --format %s %s test.yml' % (f, r)).split())

        with open(outfile, 'w') as file:
            file.write(capsys.readouterr().out)

        with open(outfile, 'r') as cf:
            flatconf = json.load(cf) if f == 'json' else yaml.safe_load(cf)
            commit = flatconf['repos']['kas3'].get('commit', None)
            envvar = flatconf['env']['TESTVAR_FOO']
            if r == '--resolve-refs':
                assert commit is not None
            else:
                assert commit is None
            if r == '--resolve-env':
                assert envvar == 'KAS'
            else:
                assert envvar == 'BAR'

            assert 'includes' not in flatconf['header']
            # check if kas can read the generated file
            if f == 'yaml':
                shutil.rmtree('%s/build' % tdir, ignore_errors=True)
                kas.kas(('checkout %s' % outfile).split())
                assert os.path.exists('build/conf/local.conf')


@pytest.mark.online
def test_lockfile(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir.mkdir('test_commands'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_repo_includes', tdir)
    monkeykas.chdir(tdir)

    # no lockfile yet, branches are floating
    kas.kas('dump test.yml'.split())
    rawspec = yaml.safe_load(capsys.readouterr().out)
    assert rawspec['repos']['externalrepo']['refspec'] == 'master'

    with open('externalrepo/.git/refs/heads/master') as f:
        expected_commit = f.readline().strip()

    # create lockfile
    kas.kas('dump --lock --inplace test.yml'.split())
    assert os.path.exists('test.lock.yml')

    # check if legacy dump -> lock redirection works
    with open('test.lock.yml', "rb") as f:
        hash_dump = file_digest_slow(f, 'sha256')
    os.remove('test.lock.yml')
    kas.kas('lock test.yml'.split())
    with open('test.lock.yml', "rb") as f:
        hash_lock = file_digest_slow(f, 'sha256')
    assert hash_dump.hexdigest() == hash_lock.hexdigest()

    # lockfile is considered during import, expect pinned branches
    kas.kas('dump test.yml'.split())
    lockspec = yaml.safe_load(capsys.readouterr().out)
    assert lockspec['overrides']['repos']['externalrepo']['commit'] \
        == expected_commit

    # insert older commit into lockfile (kas post commit/branch introduction)
    test_commit = '226e92a7f30667326a63fd9812b8cc4a6184e398'
    lockspec['overrides']['repos']['externalrepo']['commit'] = test_commit
    with open('test.lock.yml', 'w') as f:
        yaml.safe_dump(lockspec, f)

    # check if repo is moved to specified commit
    kas.kas('dump test.yml'.split())
    lockspec = yaml.safe_load(capsys.readouterr().out)
    assert lockspec['overrides']['repos']['externalrepo']['commit'] \
        == test_commit

    # update lockfile, check if repo is pinned to other commit
    kas.kas('dump --lock --inplace --update test.yml'.split())
    with open('test.lock.yml', 'r') as f:
        lockspec = yaml.safe_load(f)
        assert lockspec['overrides']['repos']['externalrepo']['commit'] \
            != test_commit


def test_root_resolve_novcs(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir.mkdir('test_root_resolve_novcs'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)

    capsys.readouterr()
    kas.kas('dump --resolve-local test-local.yml'.split())
    console = capsys.readouterr()
    assert 'not under version control' in console.err
    data = yaml.safe_load(console.out)
    assert data['repos']['local'] is None


def test_root_resolve_git(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir.mkdir('test_root_resolve_git'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)

    upstream_url = 'http://github.com/siemens/kas.git'
    subprocess.check_call(['git', 'init'])
    subprocess.check_call(['git', 'branch', '-m', 'main'])
    subprocess.check_call(['git', 'add', 'oe-init-build-env', '*.yml'])
    subprocess.check_call(['git', 'commit', '-m', 'test'])
    subprocess.check_call(['git', 'remote', 'add', 'origin', upstream_url])
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'])

    capsys.readouterr()
    kas.kas('dump --resolve-local test-local.yml'.split())
    console = capsys.readouterr()
    data = yaml.safe_load(console.out)
    assert data['repos']['local']['commit'] == commit.decode('utf-8').strip()
    assert data['repos']['local']['url'] == upstream_url

    # make repository dirty
    with open(f'{tdir}/new-file.txt', 'w') as f:
        f.write('test')
    kas.kas('dump --resolve-local test-local.yml'.split())
    console = capsys.readouterr()
    data = yaml.safe_load(console.out)
    assert data['repos']['local']['commit'] == commit.decode('utf-8').strip()
    assert data['repos']['local']['url'] == upstream_url


def test_root_resolve_hg(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir.mkdir('test_root_resolve_hg'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)

    upstream_url = 'http://github.com/siemens/kas'
    subprocess.check_call(['hg', 'init'])
    subprocess.check_call(['hg', 'add', 'test-local-hg.yml',
                           'oe-init-build-env'])
    subprocess.check_call(['hg', 'commit', '-m', 'test'])
    with open(f'{tdir}/.hg/hgrc', mode='w') as f:
        f.write(f'[paths]\ndefault = {upstream_url}')
    commit = subprocess.check_output(['hg', 'log', '-r', '.',
                                      '--template', '{node}\n'])

    capsys.readouterr()
    kas.kas('dump --resolve-local test-local-hg.yml'.split())
    console = capsys.readouterr()
    data = yaml.safe_load(console.out)
    assert data['repos']['local']['commit'] == commit.decode('utf-8').strip()
    assert data['repos']['local']['url'] == upstream_url
    assert data['repos']['local']['type'] == 'hg'

    # add all files to repository
    subprocess.check_call(['hg', 'add'])
    subprocess.check_call(['hg', 'commit', '-m', 'test2'])
    kas.kas('dump --resolve-local test-local-hg.yml'.split())


def test_ff_merges(monkeykas, tmpdir):
    """
    This tests check if kas correcly handles fast-forward merges.
    """
    tdir = tmpdir / 'test_commands'
    rdirbare = tdir / 'upstream.git'
    rdirwork = tdir / 'upstream.clone'
    wdirkas = tdir / 'kas'
    for d in [tdir, rdirbare, rdirwork, wdirkas]:
        d.mkdir()

    with open('tests/test_commands/test-ff-merges.yml', 'r') as f:
        kas_input = yaml.safe_load(f)

    shutil.copy('tests/test_commands/oe-init-build-env', rdirwork)
    # create a bare upstream repository
    monkeykas.chdir(rdirbare)
    subprocess.check_call(['git', 'init', '--bare'])
    subprocess.check_call(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'])
    # create a repository with a branch (working copy)
    monkeykas.chdir(rdirwork)
    subprocess.check_call(['git', 'init'])
    subprocess.check_call(['git', 'branch', '-m', 'main'])
    subprocess.check_call(['git', 'add', 'oe-init-build-env'])
    subprocess.check_call(['git', 'commit', '-m', 'test'])
    # get head of main branch (before merge)
    c_main = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'])
    subprocess.check_call(['git', 'checkout', '-b', 'feature'])
    subprocess.check_call(['touch', 'foo'])
    subprocess.check_call(['git', 'add', 'foo'])
    subprocess.check_call(['git', 'commit', '-m', 'test-feature'])
    # get head of feature branch
    c_feat = subprocess.check_output(['git', 'rev-parse', '--verify', 'HEAD'])
    subprocess.check_call(['git', 'remote', 'add', 'origin', rdirbare])
    subprocess.check_call(['git', 'push', 'origin', 'main', 'feature'])

    # perform initial kas checkout
    monkeykas.chdir(wdirkas)
    kas_input['repos']['upstream']['commit'] = c_main.decode('utf-8').strip()
    kas_input['repos']['upstream']['url'] = str(rdirbare)
    with open('kas.yml', 'w') as f:
        yaml.dump(kas_input, f)
    kas.kas(['checkout', 'kas.yml'])

    # ff merge feature into main
    monkeykas.chdir(rdirwork)
    # checkout main branch with kas
    subprocess.check_call(['git', 'checkout', 'main'])
    subprocess.check_call(['git', 'merge', '--ff-only', 'feature'])
    subprocess.check_call(['git', 'push', 'origin', 'main'])

    # bump commit on main branch in kas project, perform kas checkout
    monkeykas.chdir(wdirkas)
    # checkout main branch with kas again
    kas_input['repos']['upstream']['commit'] = c_feat.decode('utf-8').strip()
    with open('kas.yml', 'w') as f:
        yaml.dump(kas_input, f)
    kas.kas(['checkout', 'kas.yml'])


def test_cmd_not_found(monkeykas, tmpdir):
    cmd = ['/usr/bin/kas-not-exists']
    ret, _ = run_cmd(cmd, tmpdir, os.environ, fail=False)
    assert ret != 0
    with pytest.raises(FileNotFoundError):
        run_cmd(cmd, tmpdir, os.environ, fail=True)
