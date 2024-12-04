# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2024
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
from pathlib import Path
import shutil
import subprocess
import yaml
import pytest
from kas import kas
from kas.includehandler import IncludeException


def test_transitive_includes(monkeykas, tmpdir, capsys):
    """
    Check if a reference to a repo that itself is specified in a
    remote repo is correctly resolved.
    """
    repos = ['main', 'foo', 'bar']
    dirs = {}
    for r in repos:
        dirs[r] = Path(tmpdir / r)
        os.mkdir(dirs[r])

    # create main repo config
    with open('tests/test_transitive_includes/main.yml', 'rb') as fds:
        config_top = yaml.safe_load(fds)
    config_top['repos']['foo']['url'] = str(dirs['foo'])
    with open(dirs['main'] / 'main.yml', 'w') as config_file:
        yaml.dump(config_top, config_file)
    shutil.copy('tests/test_transitive_includes/oe-init-build-env',
                dirs['main'])

    # create foo repo and config
    with open('tests/test_transitive_includes/foo.yml', 'rb') as fds:
        config_foo = yaml.safe_load(fds)
    config_foo['repos']['bar']['url'] = str(dirs['bar'])
    with open(dirs['foo'] / 'foo.yml', 'w') as config_file:
        yaml.dump(config_foo, config_file)
    subprocess.check_call(['git', 'init'], cwd=dirs['foo'])
    subprocess.check_call(['git', 'config', 'user.email', 'test'],
                          cwd=dirs['foo'])
    subprocess.check_call(['git', 'config', 'user.name', 'test'],
                          cwd=dirs['foo'])
    subprocess.check_call(['git', 'checkout', '-b', 'kas'], cwd=dirs['foo'])
    subprocess.check_call(['git', 'add', 'foo.yml'], cwd=dirs['foo'])
    subprocess.check_call(['git', 'commit', '-m', 'init'], cwd=dirs['foo'])

    # create bar repo
    shutil.copy('tests/test_transitive_includes/bar.yml', dirs['bar'])
    subprocess.check_call(['git', 'init'], cwd=dirs['bar'])
    subprocess.check_call(['git', 'config', 'user.email', 'test'],
                          cwd=dirs['bar'])
    subprocess.check_call(['git', 'config', 'user.name', 'test'],
                          cwd=dirs['bar'])
    subprocess.check_call(['git', 'checkout', '-b', 'kas'], cwd=dirs['bar'])
    subprocess.check_call(['git', 'add', 'bar.yml'], cwd=dirs['bar'])
    subprocess.check_call(['git', 'commit', '-m', 'init'], cwd=dirs['bar'])

    monkeykas.chdir(dirs['main'])
    kas.kas(['dump', 'main.yml'])
    config_final = yaml.safe_load(capsys.readouterr().out)
    assert config_final['env']['KAS_REPO_BAR'] == "1"


def test_include_from_submodule(monkeykas, tmpdir):
    tmpdir.mkdir('main')
    tmpdir.mkdir('sub')
    for s, t in [('sub_repo.yml', 'sub'),
                 ('super_repo.yml', 'main'),
                 ('oe-init-build-env', 'main')]:
        shutil.copy(f'tests/test_transitive_includes/{s}', tmpdir / t)

    monkeykas.chdir(tmpdir / 'sub')
    subprocess.check_call(['git', 'init', '-b', 'main'])
    subprocess.check_call(['git', 'add', 'sub_repo.yml'])
    subprocess.check_call(['git', 'commit', '-m', 'init'])

    monkeykas.chdir(tmpdir / 'main')
    subprocess.check_call(['git', 'init', '-b', 'main'])

    # clone a repo as non-submodule
    subprocess.check_call(['git', 'clone', '../sub', 'sub'])
    with pytest.raises(IncludeException):
        kas.kas(['checkout', 'super_repo.yml:sub/sub_repo.yml'])

    # now add the repo as submodule
    shutil.rmtree('sub')
    subprocess.check_call(['git', '-c', 'protocol.file.allow=always',
                          'submodule', 'add', '../sub', 'sub'])
    kas.kas(['-l', 'debug', 'checkout', 'super_repo.yml:sub/sub_repo.yml'])
