# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2019
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

import pytest
import shutil
import yaml
import subprocess
from kas import kas
from kas.repos import RepoRefError, Repo


def run_cmd(cmd, cwd=None, fail=True):
    """
        Run a command and return the return code and output.
        Replacement for kas internal run_cmd function which
        cannot be used outside of kas as there is no event loop.
    """
    try:
        output = subprocess.check_output(cmd, cwd=cwd)
        return (0, output.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        if fail:
            raise e
        return (e.returncode, e.output.decode('utf-8'))


@pytest.mark.online
def test_refspec_switch(monkeykas, tmpdir):
    """
        Test that the local git clone is correctly updated when switching
        between a commit hash refspec and a branch refspec.
    """
    tdir = str(tmpdir / 'test_refspec_switch')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)

    kas.kas(['shell', 'test.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas',
                           fail=False)
    assert rc != 0
    assert output.strip() == ''
    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas',
                           fail=False)
    assert rc == 0
    assert output.strip() == '907816a5c4094b59a36aec12226e71c461c05b77'
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas2',
                           fail=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'
    (rc, output) = run_cmd(['git', 'tag', '--points-at', 'HEAD'], cwd='kas3',
                           fail=False)
    assert rc == 0
    assert output.strip() == '3.0.1'

    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas',
                           fail=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas2',
                           fail=False)
    assert rc != 0
    assert output.strip() == ''
    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas2',
                           fail=False)
    assert rc == 0
    assert output.strip() == '907816a5c4094b59a36aec12226e71c461c05b77'
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas3',
                           fail=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'
    (rc, output) = run_cmd(['git', 'tag', '--points-at', 'HEAD'], cwd='kas4',
                           fail=False)
    assert rc == 0
    assert output.strip() == '2.6.3'


@pytest.mark.online
def test_refspec_absolute(monkeykas, tmpdir):
    """
        Test that the local git clone works when a absolute refspec
        is given.
    """
    tdir = str(tmpdir / 'test_refspec_absolute')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)

    kas.kas(['shell', 'test3.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'],
                           cwd='kas_abs', fail=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'
    (rc, output_kas_abs) = run_cmd(['git', 'rev-parse', 'HEAD'],
                                   cwd='kas_abs', fail=False)
    assert rc == 0
    (rc, output_kas_rel) = run_cmd(['git', 'rev-parse', 'HEAD'],
                                   cwd='kas_rel', fail=False)
    assert rc == 0
    assert output_kas_abs.strip() == output_kas_rel.strip()
    (rc, output) = run_cmd(['git', 'tag', '--points-at', 'HEAD'],
                           cwd='kas_tag_abs', fail=False)
    assert rc == 0
    assert output.strip() == '3.0.1'


def test_url_no_refspec(monkeykas, tmpdir):
    """
        Test that a repository with url but no refspec raises an error.
    """
    tdir = str(tmpdir / 'test_url_no_refspec')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test4.yml', '-c', 'true'])


def test_commit_refspec_mix(monkeykas, tmpdir):
    """
        Test that mixing legacy refspec with commit/branch raises errors.
    """
    tdir = str(tmpdir / 'test_commit_refspec_mix')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test5.yml', '-c', 'true'])
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test6.yml', '-c', 'true'])
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test7.yml', '-c', 'true'])


@pytest.mark.online
def test_tag_commit_do_not_match(monkeykas, tmpdir):
    """
        Test that giving tag and commit that do not match raises an error.
    """
    tdir = str(tmpdir / 'test_tag_commit_do_not_match')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test8.yml', '-c', 'true'])


@pytest.mark.online
def test_unsafe_tag_warning(capsys, monkeykas, tmpdir):
    """
        Test that using tag without commit issues a warning, but only once.
    """
    tdir = str(tmpdir / 'test_unsafe_tag_warning')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    # needs to be reset in case other tests ran before
    Repo.__no_commit_tag_warned__ = []
    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    assert capsys.readouterr().err.count(
        'Using tag without commit for repository "kas4" is unsafe as tags '
        'are mutable.') == 1


@pytest.mark.online
def test_tag_branch_same_name(capsys, monkeykas, tmpdir):
    """
        Test that kas uses the tag if a branch has the same name as the tag.
    """
    tdir = str(tmpdir / 'test_tag_branch_same_name')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)

    # Checkout the repositories
    kas.kas(['shell', 'test.yml', '-c', 'true'])

    # In kas3: create a branch named "3.0.1" on master HEAD
    # A tag named "3.0.1" already exists on an old commit from 2022
    (rc, output) = run_cmd(['git', 'switch', 'master'], cwd='kas3',
                           fail=False)
    assert rc == 0
    (rc, output) = run_cmd(['git', 'branch', '3.0.1'], cwd='kas3',
                           fail=False)
    assert rc == 0

    # In kas4: create a tag named "master" on existing 2.6.3 tag
    (rc, output) = run_cmd(['git', 'checkout', '2.6.3'], cwd='kas4',
                           fail=False)
    assert rc == 0
    (rc, output) = run_cmd(['git', 'tag', 'master'], cwd='kas4',
                           fail=False)
    assert rc == 0

    # Checkout the repositories again
    kas.kas(['shell', 'test.yml', '-c', 'true'])

    # Check the commit hashes
    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas3',
                           fail=False)
    assert rc == 0
    assert output.strip() == '229310958b17dc2b505b789c1cc1d0e2fddccc44'

    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas4',
                           fail=False)
    assert rc == 0

    (rc, output2) = run_cmd(['git', 'rev-parse', 'refs/heads/master'],
                            cwd='kas4', fail=False)
    assert rc == 0
    assert output.strip() == output2.strip()


@pytest.mark.online
def test_refspec_warning(capsys, monkeykas, tmpdir):
    """
        Test that using legacy refspec issues a warning, but only once.
    """
    tdir = str(tmpdir / 'test_refspec_warning')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    # needs to be reset in case other tests ran before
    Repo.__legacy_refspec_warned__ = []
    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    assert capsys.readouterr().err.count(
        'Using deprecated refspec for repository "kas2".') == 1


@pytest.mark.online
def test_branch_and_tag(monkeykas, tmpdir, mercurial):
    """
        Test if error is raised when branch and tag are set.
    """
    tdir = str(tmpdir / 'test_branch_and_tag')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    with mercurial(tmpdir, 'evolve', branch='stable'):
        with pytest.raises(RepoRefError):
            kas.kas(['checkout', 'test9.yml'])

    with pytest.raises(RepoRefError):
        kas.kas(['checkout', 'test10.yml'])

    with pytest.raises(RepoRefError):
        kas.kas(['checkout', 'test11.yml'])


@pytest.mark.online
def test_commit_expand(monkeykas, tmpdir, capsys):
    """
        Test if an abbreviated commit hash is expanded to the full hash.
    """
    tdir = str(tmpdir / 'test_commit_expand')
    shutil.copytree('tests/test_refspec', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['dump', '--resolve-refs', 'test12.yml'])
    rawspec = yaml.safe_load(capsys.readouterr().out)
    assert rawspec['repos']['kas']['commit'] == \
        'abd109469d17b7ff4d958b5aa5ab5f5511cc4d43'
