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


class DoKas:
    def __init__(self, monkeykas, tmpdir):
        self.tmpdir = tmpdir
        self.monkeykas = monkeykas

    def run(self, filename):
        tdir = str(self.tmpdir / 'test_layers')
        shutil.copytree('tests/test_layers', tdir)
        self.monkeykas.chdir(tdir)
        self.monkeykas.setenv('KAS_CLONE_DEPTH', '1')
        kas.kas(['shell', filename, '-c', 'true'])
        # extract layer path from bblayers, keep order
        with open(self.monkeykas.get_kbd() / 'conf/bblayers.conf', 'r') as f:
            return [x.strip(' \\"\n').replace(LAYERBASE, '')
                    for x in f.readlines() if x.lstrip().startswith(LAYERBASE)]


@pytest.fixture
def dokas(monkeykas, tmpdir):
    return DoKas(monkeykas, tmpdir)


@pytest.mark.online
def test_layers_default(dokas):
    layers = dokas.run('test.yml')
    assert len([l_ for l_ in layers if l_ == '/kas']) == 1


@pytest.mark.online
def test_layers_include(dokas):
    layers = dokas.run('test.yml')
    assert len([l_ for l_ in layers if '/kas1/meta-' in l_]) == 2


@pytest.mark.online
def test_layers_exclude(dokas):
    layers = dokas.run('test.yml')
    assert not any([l_ for l_ in layers if '/kas2' in l_])


@pytest.mark.online
def test_layers_strip_dot(dokas):
    layers = dokas.run('test.yml')
    assert any([l_ for l_ in layers if l_ == '/kas3'])
    assert any([l_ for l_ in layers if l_ == '/kas3/meta-bar'])


@pytest.mark.online
def test_layers_order(dokas):
    layers = dokas.run('test.yml')
    # layers of a repo are sorted alphabetically
    assert layers[1] == '/kas1/meta-bar'
    assert layers[2] == '/kas1/meta-foo'
    # repos are sorted alphabetically (aa-kas from kas4 is last)
    assert layers[-1] == '/aa-kas/meta'


@pytest.mark.online
def test_layers_prio(dokas, monkeykas):
    layers = dokas.run('test-layer-prio.yml')
    # layers are sorted by global priority
    # highest prio (10)
    assert layers[0] == '/02-kas/meta-foo'
    # no prio, sorted alphabetically by repo name, layer name
    assert layers[1] == '/01-kas/aa-test'
    assert layers[2] == '/01-kas/zz-test'
    # default prio as not explicitly specified, sorted by repo name
    assert layers[3] == ''
    # lower than default prio (-10)
    assert layers[4] == '/01-kas'
    # even lower (-20)
    assert layers[5] == '/02-kas/meta-bar'
