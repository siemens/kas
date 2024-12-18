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

import os
import stat
import shutil
import pytest
import subprocess
from kas import kas
from kas.repos import PatchApplyError, PatchFileNotFound, PatchMappingError


def git_get_commit(path):
    output = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=path)
    return output.decode('utf-8').strip()


def mercurial_get_commit(path):
    output = subprocess.check_output(
        ['hg', 'log', '-r', '.', '--template', '{node}\n'], cwd=path)
    return output.decode('utf-8').strip()


@pytest.mark.online
def test_patch(monkeykas, tmpdir, mercurial):
    tdir = str(tmpdir / 'test_patch')
    shutil.copytree('tests/test_patch', tdir)
    monkeykas.chdir(tdir)

    repo = mercurial(tmpdir, 'example')
    commit = repo.get_commit()
    subprocess.check_call(
        ['sed', '-i', f's/82e55d328c8c/{commit}/', 'test.yml'])

    kas.kas(['shell', 'test.yml', '-c', 'true'])
    for f in ['kas/tests/test_patch/hello.sh', 'hello/hello.sh']:
        assert os.stat(f)[stat.ST_MODE] & stat.S_IXUSR

    kas_head_ref = git_get_commit("kas")
    kas_branch_head_ref = git_get_commit("kas-branch")
    hello_head_ref = mercurial_get_commit("hello")
    hello_branch_head_ref = mercurial_get_commit("hello-branch")

    kas.kas(['shell', 'test.yml', '-c', 'true'])

    assert git_get_commit("kas") == kas_head_ref
    assert git_get_commit("kas-branch") == kas_branch_head_ref
    assert mercurial_get_commit("hello") == hello_head_ref
    assert mercurial_get_commit("hello-branch") == hello_branch_head_ref


@pytest.mark.online
def test_patch_update(monkeykas, tmpdir, mercurial):
    """
        Test that patches are applied correctly after switching a repo from
        a branch to a commit hash and vice-versa with both git and mercurial
        repositories.
    """
    tdir = str(tmpdir / 'test_patch_update')
    shutil.copytree('tests/test_patch', tdir)
    monkeykas.chdir(tdir)

    repo = mercurial(tmpdir, 'example')
    commit = repo.get_commit()
    for file, c in [('test.yml', '82e55d328c8c'),
                    ('test2.yml', '0a04b987be5a')]:
        subprocess.check_call(
            ['sed', '-i', f's/{c}/{commit}/', file])

    kas.kas(['shell', 'test.yml', '-c', 'true'])
    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    for f in ['kas/tests/test_patch/hello.sh', 'hello/hello.sh']:
        assert os.stat(f)[stat.ST_MODE] & stat.S_IXUSR


@pytest.mark.online
def test_invalid_patch(monkeykas, tmpdir):
    """
        Test on common errors when applying patches
    """
    tdir = str(tmpdir / 'test_patch_invalid')
    shutil.copytree('tests/test_patch', tdir)
    monkeykas.chdir(tdir)

    with pytest.raises(PatchFileNotFound):
        kas.kas(['shell', 'test-invalid.yml', '-c', 'true'])

    with pytest.raises(PatchMappingError):
        kas.kas(['shell', 'test-invalid2.yml', '-c', 'true'])

    with pytest.raises(PatchApplyError):
        kas.kas(['shell', 'test-invalid3.yml', '-c', 'true'])


@pytest.mark.online
def test_patch_dirty_repo(monkeykas, tmpdir, mercurial):
    """
        Test that kas will not apply patches to a dirty repository
    """
    tdir = str(tmpdir / 'test_patch_dirty')
    shutil.copytree('tests/test_patch', tdir)
    monkeykas.chdir(tdir)

    repo = mercurial(tmpdir, 'example')
    commit = repo.get_commit()
    subprocess.check_call(
        ['sed', '-i', f's/82e55d328c8c/{commit}/', 'test.yml'])

    kas.kas(['checkout', '--skip', 'repos_apply_patches', 'test.yml'])
    with open('kas-branch/README.rst', 'a') as f:
        f.write('echo "dirty"')
    kas.kas(['checkout', 'test.yml'])
    # the dirty repo must not be patched
    assert not os.path.exists('kas-branch/tests/test_patch/hello.sh')
    # the clean repo must be patched
    assert os.path.exists('hello-branch/hello.sh')
