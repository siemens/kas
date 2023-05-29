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
from kas import kas
from kas.repos import PatchApplyError, PatchFileNotFound, PatchMappingError


def test_patch(changedir, tmpdir):
    tdir = str(tmpdir / 'test_patch')
    shutil.copytree('tests/test_patch', tdir)
    cwd = os.getcwd()
    os.chdir(tdir)
    kas.kas(['shell', 'test.yml', '-c', 'true'])
    for f in ['kas/tests/test_patch/hello.sh', 'hello/hello.sh']:
        assert os.stat(f)[stat.ST_MODE] & stat.S_IXUSR
    kas.kas(['shell', 'test.yml', '-c', 'true'])
    os.chdir(cwd)


def test_patch_update(changedir, tmpdir):
    """
        Test that patches are applied correctly after switching a repo from
        a branch to a commit hash and vice-versa with both git and mercurial
        repositories.
    """
    tdir = str(tmpdir / 'test_patch_update')
    shutil.copytree('tests/test_patch', tdir)
    cwd = os.getcwd()
    os.chdir(tdir)
    kas.kas(['shell', 'test.yml', '-c', 'true'])
    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    for f in ['kas/tests/test_patch/hello.sh', 'hello/hello.sh']:
        assert os.stat(f)[stat.ST_MODE] & stat.S_IXUSR
    os.chdir(cwd)


def test_invalid_patch(changedir, tmpdir):
    """
        Test on common errors when applying patches
    """
    tdir = str(tmpdir / 'test_patch_invalid')
    shutil.copytree('tests/test_patch', tdir)
    cwd = os.getcwd()
    os.chdir(tdir)

    with pytest.raises(PatchFileNotFound):
        kas.kas(['shell', 'test-invalid.yml', '-c', 'true'])

    with pytest.raises(PatchMappingError):
        kas.kas(['shell', 'test-invalid2.yml', '-c', 'true'])

    with pytest.raises(PatchApplyError):
        kas.kas(['shell', 'test-invalid3.yml', '-c', 'true'])
    os.chdir(cwd)
