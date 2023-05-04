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
import pytest
import shutil
from kas import kas
from kas.libkas import run_cmd
from kas.repos import RepoRefError


def test_refspec_switch(changedir, tmpdir):
    """
        Test that the local git clone is correctly updated when switching
        between a commit hash refspec and a branch refspec.
    """
    tdir = str(tmpdir / 'test_refspec_switch')
    shutil.copytree('tests/test_refspec', tdir)
    os.chdir(tdir)

    kas.kas(['shell', 'test.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas',
                           fail=False, liveupdate=False)
    assert rc != 0
    assert output.strip() == ''
    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas',
                           fail=False, liveupdate=False)
    assert rc == 0
    assert output.strip() == '907816a5c4094b59a36aec12226e71c461c05b77'
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas2',
                           fail=False, liveupdate=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'

    kas.kas(['shell', 'test2.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas',
                           fail=False, liveupdate=False)
    assert rc == 0
    assert output.strip() == 'refs/heads/master'
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'], cwd='kas2',
                           fail=False, liveupdate=False)
    assert rc != 0
    assert output.strip() == ''
    (rc, output) = run_cmd(['git', 'rev-parse', 'HEAD'], cwd='kas2',
                           fail=False, liveupdate=False)
    assert rc == 0
    assert output.strip() == '907816a5c4094b59a36aec12226e71c461c05b77'


def test_refspec_absolute(changedir, tmpdir):
    """
        Test that the local git clone works when a absolute refspec
        is given.
    """
    tdir = str(tmpdir / 'test_refspec_absolute')
    shutil.copytree('tests/test_refspec', tdir)
    os.chdir(tdir)

    kas.kas(['shell', 'test3.yml', '-c', 'true'])
    (rc, output) = run_cmd(['git', 'symbolic-ref', '-q', 'HEAD'],
                           cwd='kas_abs', fail=False, liveupdate=False)
    assert rc != 0
    assert output.strip() == ''
    (rc, output_kas_abs) = run_cmd(['git', 'rev-parse', 'HEAD'],
                                   cwd='kas_abs', fail=False, liveupdate=False)
    assert rc == 0
    (rc, output_kas_rel) = run_cmd(['git', 'rev-parse', 'HEAD'],
                                   cwd='kas_rel', fail=False, liveupdate=False)
    assert rc == 0
    assert output_kas_abs.strip() == output_kas_rel.strip()


def test_url_no_refspec(changedir, tmpdir):
    """
        Test that a repository with url but no refspec raises an error.
    """
    tdir = str(tmpdir / 'test_url_no_refspec')
    shutil.copytree('tests/test_refspec', tdir)
    os.chdir(tdir)
    with pytest.raises(RepoRefError):
        kas.kas(['shell', 'test4.yml', '-c', 'true'])
