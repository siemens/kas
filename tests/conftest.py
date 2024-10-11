# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2019-2024
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
import os
import subprocess

ENVVARS_KAS = [
    'KAS_WORK_DIR',
    'KAS_BUILD_DIR',
    'KAS_REPO_REF_DIR',
    'KAS_DISTRO',
    'KAS_MACHINE',
    'KAS_TARGET',
    'KAS_TASK',
    'KAS_PREMIRRORS',
    'KAS_CLONE_DEPTH',
    'SSH_PRIVATE_KEY',
    'SSH_PRIVATE_KEY_FILE',
    'SSH_AUTH_SOCK',
    'CI_SERVER_HOST',
    'CI_JOB_TOKEN',
    'GITLAB_CI',
    'GITHUB_ACTIONS',
    'REMOTE_CONTAINERS'
]

ENVVARS_TOOLS = [
    'EMAIL'
]


@pytest.fixture
def monkeykas(monkeypatch, tmpdir):
    for var in ENVVARS_KAS + ENVVARS_TOOLS:
        monkeypatch.delenv(var, raising=False)
    # Set HOME to a temporary directory
    homedir = tmpdir / '_home'
    homedir.mkdir()
    monkeypatch.setenv('HOME', str(homedir))

    # remove all VSCode devcontainers related variables
    for var in os.environ.keys():
        if var.startswith('REMOTE_CONTAINERS_'):
            monkeypatch.delenv(var)
    # remove all git related variables
    for var in os.environ.keys():
        if var.startswith('GIT_'):
            monkeypatch.delenv(var)
    # provide minimal git environment
    monkeypatch.setenv('GIT_AUTHOR_NAME', 'kas')
    monkeypatch.setenv('GIT_AUTHOR_EMAIL', 'kas@example.com')
    monkeypatch.setenv('GIT_COMMITTER_NAME', 'kas')
    monkeypatch.setenv('GIT_COMMITTER_EMAIL', 'kas@example.com')

    yield monkeypatch


class MercurialRepo:
    """
    Create a new Mercurial repository with a single commit.
    """
    def __init__(self, tmpdir, name, branch=None):
        """
        Creates a new Mercurial repository with a single commit.
        The content resembles the Makefile from the hello world example.
        """
        self.repo = tmpdir / name
        self.repo.mkdir()
        subprocess.check_call(['hg', 'init'], cwd=self.repo)
        if branch:
            subprocess.check_call(['hg', 'branch', branch], cwd=self.repo)
        with open(self.repo / 'Makefile', 'w') as f:
            f.write('all:\n\techo hello\n')
        subprocess.check_call(['hg', 'add', 'Makefile'], cwd=self.repo)
        subprocess.check_call(['hg', '--config', 'ui.username=kas',
                               'commit', '-m', 'initial commit',
                               '--date', '2024-11-10 08:00'], cwd=self.repo)

    def __enter__(self):
        return self.repo

    def get_commit(self):
        return subprocess.check_output(
            ['hg', 'log', '-r', '.', '--template', '{rev}:{node}'],
            cwd=self.repo).decode('utf-8').strip()

    def __exit__(self, exc_type, exc_value, traceback):
        self.repo.remove()


@pytest.fixture
def mercurial():
    def make_hg_repo(tmpdir, name, branch=None):
        return MercurialRepo(tmpdir, name, branch)
    return make_hg_repo
