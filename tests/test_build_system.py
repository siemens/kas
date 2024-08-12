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


def test_build_system(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_build_system')
    shutil.copytree('tests/test_build_system', tdir)
    monkeykas.chdir(tdir)

    kas.kas(['shell', 'test-oe.yml', '-c', 'true'])
    with open('build-env', 'r') as f:
        assert f.readline().strip() == 'openembedded'

    kas.kas(['shell', 'test-isar.yml', '-c', 'true'])
    with open('build-env', 'r') as f:
        assert f.readline().strip() == 'isar'

    kas.kas(['shell', 'test-openembedded.yml', '-c', 'true'])
    with open('build-env', 'r') as f:
        assert f.readline().strip() == 'openembedded'


def test_gitconfig(monkeykas, tmpdir, capsys):
    tdir = str(tmpdir / 'test_gitconfig')
    shutil.copytree('tests/test_build_system', tdir)
    monkeykas.chdir(tdir)

    kas.kas(['shell', 'test-oe.yml', '-c',
             f'git config --get user.name > {tdir}/user.name'])
    with open(f'{tdir}/user.name', 'r') as f:
        assert f.readline().strip() == 'kas User'

    monkeykas.setenv('GITCONFIG_FILE', f'{tdir}/gitconfig')
    with open(f'{tdir}/gitconfig', 'w') as f:
        f.write('[user]\n')
        f.write('\temail = kas@kastest.io\n')
        f.write('[url "git@github.com:"]\n')
        f.write('\tinsteadOf = git://github\n')
        f.write('\tinsteadOf = git://github.io\n')
    kas.kas(['shell', 'test-oe.yml', '-c',
             f'git config --get user.email > {tdir}/user.email'])
    kas.kas(['shell', 'test-oe.yml', '-c',
             'git config --get-all "url.git@github.com:.insteadof" '
             f'> {tdir}/url'])
    # check if user is restored after patching
    with open(f'{tdir}/user.email', 'r') as f:
        assert f.readline().strip() == 'kas@kastest.io'
    # check the multi-key url rewrites
    with open(f'{tdir}/url', 'r') as f:
        assert f.readline().strip() == 'git://github'
        assert f.readline().strip() == 'git://github.io'
