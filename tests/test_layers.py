# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2020
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
from kas import kas

import pytest

LAYERBASE = '${TOPDIR}/..'


@pytest.fixture
def dokas(tmpdir):
    tdir = str(tmpdir.mkdir('test_layers'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_layers', tdir)
    os.chdir(tdir)
    kas.kas(['shell', 'test.yml', '-c', 'true'])
    yield
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))


def test_layers_default(dokas):
    match = 0
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            if '{}/kas '.format(LAYERBASE) in line:
                match += 1
    assert(match == 1)


def test_layers_include(dokas):
    match = 0
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            if '{}/kas1/meta-'.format(LAYERBASE) in line:
                match += 1
    assert(match == 2)


def test_layers_exclude(dokas):
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            assert('{}/kas2'.format(LAYERBASE) not in line)


def test_layers_strip_dot(dokas):
    with open('build/conf/bblayers.conf', 'r') as f:
        lines = f.readlines()
        assert(any('{}/kas3 '.format(LAYERBASE) in x for x in lines))
        assert(any('{}/kas3/meta-bar'.format(LAYERBASE) in x for x in lines))
