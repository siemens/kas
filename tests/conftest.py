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

ENVVARS_KAS = [
    'KAS_WORK_DIR',
    'KAS_BUILD_DIR',
    'KAS_REPO_REF_DIR',
    'KAS_DISTRO',
    'KAS_MACHINE',
    'KAS_TARGET',
    'KAS_TASK',
    'KAS_PREMIRRORS',
    'SSH_PRIVATE_KEY',
    'SSH_PRIVATE_KEY_FILE',
    'SSH_AUTH_SOCK',
    'CI_SERVER_HOST',
    'CI_JOB_TOKEN',
    'GITLAB_CI',
    'GITHUB_ACTIONS'
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
