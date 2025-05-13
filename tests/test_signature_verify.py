# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens, 2025
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
import shutil
import yaml
import gnupg
from pathlib import Path
from subprocess import check_output
from kas import kas
from kas.repos import RepoRefError
from kas.kasusererror import KasUserError
from kas.keyhandler import KeyImportError


@pytest.mark.online
def test_signed_gpg_invalid(monkeykas, tmpdir):
    tdir = tmpdir / 'test_signature_verify'
    shutil.copytree('tests/test_signature_verify', tdir)
    monkeykas.chdir(tdir)
    with pytest.raises(RepoRefError):
        kas.kas(['checkout', 'test-gpg-wrong-key.yml'])


@pytest.mark.online
def test_signed_gpg_remove_key(monkeykas, tmpdir):
    tdir = tmpdir / 'test_signature_verify'
    shutil.copytree('tests/test_signature_verify', tdir)
    monkeykas.chdir(tdir)

    # successfully validate signature
    kas.kas(['checkout', 'test-gpg-key-retention.yml'])

    # change key in config and try again
    with open('test-gpg-key-retention.yml', 'r') as f:
        data = yaml.safe_load(f)
        # use OEs signing key
        data['signers']['jan-kiszka']['fingerprint'] = \
            '2AFB13F28FBBB0D1B9DAF63087EB3D32FB631AD9'
    with open('test-gpg-key-retention.yml', 'w') as f:
        yaml.dump(data, f)
    with pytest.raises(RepoRefError):
        kas.kas(['checkout', 'test-gpg-key-retention.yml'])

    # remove key from config and try again (without deleting the keystore)
    with open('test-gpg-key-retention.yml', 'r') as f:
        data = yaml.safe_load(f)
        del data['signers']
    with open('test-gpg-key-retention.yml', 'w') as f:
        yaml.dump(data, f)
    with pytest.raises(KasUserError):
        kas.kas(['checkout', 'test-gpg-key-retention.yml'])


@pytest.mark.dirsfromenv
@pytest.mark.online
def test_signed_gpg_local_key(monkeykas, tmpdir):
    tdir = tmpdir / 'test_signature_verify'
    shutil.copytree('tests/test_signature_verify', tdir)
    monkeykas.chdir(tdir)
    # we don't want to store keys in this repo, hence download a key,
    # export it and pass to kas
    KEY_FINGERPRINT = 'CA5F8C00F5FBC85466016C808AD4AC6F7AE5E714'
    gnupghome = tdir / 'test_gnupg'
    gnupghome.mkdir()
    gnupghome.chmod(0o700)
    gpg = gnupg.GPG(gnupghome=str(gnupghome))
    gpg.recv_keys('keyserver.ubuntu.com', KEY_FINGERPRINT)
    gpg.export_keys(KEY_FINGERPRINT, armor=True,
                    output=str(tdir / 'jan-kiszka.asc'))

    with pytest.raises(KeyImportError):
        kas.kas(['checkout', 'test-gpg-local-key.yml'])

    # remove key definition with wrong fingerprint
    with open('test-gpg-local-key.yml', 'r') as f:
        data = yaml.safe_load(f)
        del data['signers']['wrong-fp']
    with open('test-gpg-local-key.yml', 'w') as f:
        yaml.dump(data, f)
    kas.kas(['checkout', 'test-gpg-local-key.yml'])


@pytest.mark.dirsfromenv
def test_signed_ssh_key(monkeykas, tmpdir):
    tdir = tmpdir / 'test_signature_verify'
    shutil.copytree('tests/test_signature_verify', tdir)
    monkeykas.chdir(tdir)
    kas_wd = monkeykas.get_kwd()

    repodir = Path(kas_wd / 'testrepo')
    repodir.mkdir()
    # create a new ssh key
    sshdir = Path(tdir / 'ssh')
    sshdir.mkdir()
    sshdir.chmod(0o700)

    monkeykas.chdir(repodir)
    check_output(['ssh-keygen', '-t', 'rsa', '-N', '', '-C', 'Comment Space',
                  '-f', str(sshdir / 'testkey')])
    # create a git repository with a single commit
    check_output(['git', 'init'])
    check_output(['git', 'config', 'user.name', 'kas'])
    check_output(['git', 'config', 'user.email', 'kas@example.com'])
    check_output(['git', 'config', 'gpg.format', 'ssh'])
    check_output(['git', 'config', 'user.signingkey', str(sshdir / 'testkey')])
    check_output(['git', 'commit', '-S', '-m', 'initial commit',
                  '--allow-empty'])
    check_output(['git', 'tag', '-s', 'signed-tag', '-m', 'signed tag'])
    monkeykas.chdir(tdir)

    kas.kas(['checkout', 'test-ssh-key.yml'])

    # now replace the ssh key and check if signature verification fails
    (sshdir / 'testkey').unlink()
    (sshdir / 'testkey.pub').unlink()
    check_output(['ssh-keygen', '-t', 'rsa', '-N', '', '-f',
                  str(sshdir / 'testkey')])

    with pytest.raises(RepoRefError):
        kas.kas(['checkout', 'test-ssh-key.yml'])
