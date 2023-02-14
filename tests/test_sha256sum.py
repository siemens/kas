# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2023
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
import sys
from kas import kas


class OutputRecorder:
    def __init__(self):
        self.buffer = ''

    def write(self, buffer):
        print(">>> " + buffer)
        self.buffer += buffer

    def flush(self):
        pass


def test_valid_sha256sum(changedir, tmpdir):
    """
        Test that a sha256sum is validated
    """
    tdir = str(tmpdir / 'test_valid_sha256sum')
    shutil.copytree('tests/test_sha256sum', tdir)
    os.chdir(tdir)

    recorder = OutputRecorder()
    stderr = sys.stderr
    sys.stderr = recorder

    kas.kas(['shell', 'test1.yml', '-c', 'true'])
    assert 'Checkout checksum of repository kas validated' in recorder.buffer
    assert 'Checkout checksum of repository hello validated' in recorder.buffer

    sys.stderr = stderr


def test_invalid_sha256sum(changedir, tmpdir):
    """
        Test that a sha256sum is validated
    """
    tdir = str(tmpdir / 'test_valid_sha256sum')
    shutil.copytree('tests/test_sha256sum', tdir)
    os.chdir(tdir)

    recorder = OutputRecorder()
    stderr = sys.stderr
    sys.stderr = recorder

    with pytest.raises(SystemExit):
        kas.kas(['shell', 'test2.yml', '-c', 'true'])
        assert 'Checksum mismatch for repository kas' in recorder.buffer
    with pytest.raises(SystemExit):
        recorder.buffer = ''
        kas.kas(['shell', 'test3.yml', '-c', 'true'])
        assert 'Checksum mismatch for repository hello' in recorder.buffer

    sys.stderr = stderr
