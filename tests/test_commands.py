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
import pytest
from kas import kas
from kas.libkas import TaskExecError


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


def test_for_all_repos_keep_config_unchanged(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_commands', tdir)
    monkeykas.chdir(tdir)

    with pytest.raises(FileNotFoundError, match=r'.*/kas_1.[01]'):
        kas.kas(['for-all-repos', '--keep-config-unchanged', 'test.yml',
                 'pwd'])

    assert not os.path.exists('kas_1.0')
    assert not os.path.exists("kas_1.1")


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


def test_checkout_create_refs(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    repo_cache = pathlib.Path(str(tmpdir.mkdir('repos')))
    shutil.copytree('tests/test_patch', tdir)
    monkeykas.chdir(tdir)
    monkeykas.setenv('KAS_REPO_REF_DIR', str(repo_cache))
    kas.kas(['checkout', 'test.yml'])
    assert os.path.exists(str(repo_cache / 'github.com.siemens.kas.git'))
    assert os.path.exists('kas/.git/objects/info/alternates')


def test_repo_includes(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_commands')
    shutil.copytree('tests/test_repo_includes', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['checkout', 'test.yml'])


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
