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

import shutil
import pytest
import json
from kas import kas
from kas.kasusererror import ArtifactNotFoundError

BITBAKE_OPTIONS_SHA256 = "e35d535e81cfdc4ed304af8000284c36" \
                         "19d2c4c78392ddcefe9ca46b158235f8"


def test_artifact_node(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_build')
    shutil.copytree('tests/test_build', tdir)
    monkeykas.chdir(tdir)
    kas.kas(['build', 'artifact-named.yml'])
    kas.kas(['build', 'artifact-glob.yml'])
    kas.kas(['build', 'artifact-invalid.yml'])


@pytest.mark.online
def test_provenance(monkeykas, tmpdir):
    tdir = str(tmpdir / 'test_build')
    shutil.copytree('tests/test_build', tdir)
    monkeykas.chdir(tdir)

    with pytest.raises(ArtifactNotFoundError):
        kas.kas(['build', '--provenance', 'mode=min',
                 'artifact-invalid.yml'])

    kas.kas(['build', '--provenance', 'mode=min', 'provenance.yml'])
    with open('build/attestation/kas-build.provenance.json', 'r') as f:
        prov = json.load(f)
        assert prov['subject'][0]['name'] == 'bitbake.options'
        assert 'env' not in \
            prov['predicate']['buildDefinition']['internalParameters']

    with monkeykas.context() as mp:
        mp.setenv('CAPTURE_THIS', 'OK Sir!')
        kas.kas(['build', '--provenance', 'mode=max', 'provenance.yml'])
    with open('build/attestation/kas-build.provenance.json', 'r') as f:
        prov = json.load(f)
        params = prov['predicate']['buildDefinition']['internalParameters']
        assert params['env']['CAPTURE_THIS'] == 'OK Sir!'
        assert prov['subject'][0]['name'] == 'bitbake.options'
        assert prov['subject'][0]['digest']['sha256'] == BITBAKE_OPTIONS_SHA256
