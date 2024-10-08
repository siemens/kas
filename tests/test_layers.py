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

import shutil
from kas import kas

import pytest

LAYERBASE = '${TOPDIR}/..'


@pytest.fixture
def dokas(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_layers')
    shutil.copytree('tests/test_layers', tdir)
    monkeykas.chdir(tdir)
    monkeykas.setenv('KAS_CLONE_DEPTH', '1')
    kas.kas(['shell', 'test.yml', '-c', 'true'])


@pytest.mark.online
def test_layers_default(dokas):
    match = 0
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            if f'{LAYERBASE}/kas ' in line:
                match += 1
    assert match == 1


@pytest.mark.online
def test_layers_include(dokas):
    match = 0
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            if f'{LAYERBASE}/kas1/meta-' in line:
                match += 1
    assert match == 2


@pytest.mark.online
def test_layers_exclude(dokas):
    with open('build/conf/bblayers.conf', 'r') as f:
        for line in f:
            assert f'{LAYERBASE}/kas2' not in line


@pytest.mark.online
def test_layers_strip_dot(dokas):
    with open('build/conf/bblayers.conf', 'r') as f:
        lines = f.readlines()
        assert any(f'{LAYERBASE}/kas3 ' in x for x in lines)
        assert any(f'{LAYERBASE}/kas3/meta-bar' in x for x in lines)


@pytest.mark.online
def test_layers_order(dokas):
    with open('build/conf/bblayers.conf', 'r') as f:
        layers = [x.strip(' \\"\n').replace(LAYERBASE, '')
                  for x in f.readlines() if x.lstrip().startswith(LAYERBASE)]
        # layers of a repo are sorted alphabetically
        assert layers[1] == '/kas1/meta-bar'
        assert layers[2] == '/kas1/meta-foo'
        # repos are sorted alphabetically (aa-kas from kas4 is last)
        assert layers[-1] == '/aa-kas/meta'
