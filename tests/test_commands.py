# kas - setup tool for bitbake based projects
#
# Copyright (c) Konsulko Group, 2020
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

import glob
import os
import shutil
from kas import kas


def test_for_all_repos(changedir, tmpdir):
    tdir = str(tmpdir.mkdir('test_commands'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_commands', tdir)
    os.chdir(tdir)
    kas.kas(['for-all-repos', 'test.yml',
             '''if [ -n "${KAS_REPO_URL}" ]; then git rev-parse HEAD \
                     >> %s/ref_${KAS_REPO_NAME}; fi''' % (tdir)])

    with open('ref_kas_1.0', 'r') as f:
        assert(f.readline().strip()
               == '907816a5c4094b59a36aec12226e71c461c05b77')
    with open('ref_kas_1.1', 'r') as f:
        assert(f.readline().strip()
               == 'e9ca55a239caa1a2098e1d48773a29ea53c6cab2')


def test_checkout(changedir, tmpdir):
    tdir = str(tmpdir.mkdir('test_commands'))
    shutil.rmtree(tdir, ignore_errors=True)
    shutil.copytree('tests/test_commands', tdir)
    os.chdir(tdir)
    kas.kas(['checkout', 'test.yml'])

    # Ensure that local.conf and bblayers.conf are populated, check that no
    # build has been executed by ensuring that no tmp, sstate-cache or
    # downloads directories are present.
    assert(os.path.exists('build/conf/local.conf'))
    assert(os.path.exists('build/conf/bblayers.conf'))
    assert(not glob.glob('build/tmp*'))
    assert(not os.path.exists('build/downloads'))
    assert(not os.path.exists('build/sstate-cache'))
