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
"""
    This module provide the infrastructure to setup and work with local
    GnuPG keyrings.
"""

import logging
import subprocess
from pathlib import Path
from git.config import GitConfigParser
from kas.kasusererror import KasUserError, MissingModuleError

try:
    import gnupg
    HAVE_GNUPG = True
except ImportError:
    HAVE_GNUPG = False


class KeyImportError(KasUserError):
    """
    Raised when a key could not be imported.
    """
    def __init__(self, name, message):
        super().__init__(f'Could not import key "{name}": {message}')


class KeyHandler:
    @property
    def env(self):
        return {}

    def prepare_validation(self, repo):
        """
        Configure the repository for signature validation (e.g.
        define set of allowed keys). Currently only supported for
        git repos.
        """
        if repo.get_type() != 'git':
            raise KasUserError('Only git repositories are supported')

    def validate_allowed_signer(self, repo, output):
        """
        Process the output of a signature validation and validate
        it against the list of allowed signers. Must only be called
        if the validation by the VCS was completed successfully.
        """
        assert repo.get_type() == 'git'

    def get_key_repr(self, keyname):
        """
        Returns a human readable representation of the key. Derived
        classes may override this to provide a more meaningful
        representation of the key.
        """
        return keyname


class GPGKeyHandler(KeyHandler):
    def __init__(self, gnupghome, signers, confinst):
        if not HAVE_GNUPG:
            raise MissingModuleError('python-gnupg', 'signature verification')

        if logging.getLogger().level <= logging.DEBUG:
            logging.getLogger('gnupg').setLevel(logging.INFO)

        self.gpg = gnupg.GPG(gnupghome=str(gnupghome))
        self.fingerprints = {}
        self._reset_trust()
        self._import_keys(signers, confinst)

    def _reset_trust(self):
        all_keys = self.gpg.list_keys()
        for key in all_keys:
            fingerprint = key['fingerprint']
            logging.debug(f'Resetting trust level for key "{fingerprint}"')
            self.gpg.trust_keys(fingerprint, 'TRUST_NEVER')

    def _import_keys(self, signers, confinst):
        for name, loc in signers.items():
            fingerprint = loc.get('fingerprint')
            keyserver = loc.get('gpg_keyserver')
            if 'path' in loc:
                if 'repo' not in loc:
                    raise KasUserError('path must be used together with repo')
                repo = confinst.get_repo(loc['repo'])
                keyfile = Path(repo.path) / Path(loc['path'])
                import_result = self.gpg.import_keys_file(keyfile)
            elif keyserver:
                if not fingerprint:
                    raise KasUserError('"gpg_keyserver" must be used together '
                                       'with "fingerprint"')
                import_result = self.gpg.recv_keys(keyserver,
                                                   fingerprint)
            if import_result.count == 0:
                raise KeyImportError(name, 'No keys imported')
            if import_result.count > 1:
                raise KeyImportError(name,
                                     'Multiple keys imported')
            # an import result can also have expired keys which are not
            # imported but show up in the results array. Ignore them.
            actual_fp = [k for k in import_result.results
                         if k['fingerprint']][0]['fingerprint']

            if fingerprint and actual_fp != fingerprint:
                raise KeyImportError(name,
                                     'Fingerprints do not match: '
                                     f'Key has "{actual_fp}". '
                                     f'Expected "{fingerprint}".')
            # we operate on a kas-local keystore, so we can trust the key
            self.gpg.trust_keys(actual_fp, 'TRUST_ULTIMATE')
            self.fingerprints[name] = actual_fp
            logging.debug(f'Imported key "{name}" with fingerprint '
                          f'"{actual_fp}"')

    def _fingerprint(self, keyname):
        fingerprint = self.fingerprints.get(keyname)
        if not fingerprint:
            raise KasUserError(f'Key "{keyname}" not found')
        return self.gpg.list_keys(keys=fingerprint)[0]['fingerprint']

    def _keyid(self, fingerprint):
        keyname = [k for k, v in self.fingerprints.items()
                   if v == fingerprint]
        if not keyname:
            return None
        return keyname[0]

    @property
    def env(self):
        return {'GNUPGHOME': str(self.gpg.gnupghome)}

    def validate_allowed_signer(self, repo, output):
        super().validate_allowed_signer(repo, output)
        allowed_fps = [self._fingerprint(x) for x in repo.allowed_signers]
        validsigs = [x for x in output.split('\n') if 'VALIDSIG' in x]
        sigs = [x.split()[-1] for x in validsigs]
        if not sigs:
            return (False, None)
        for sig in sigs:
            if sig in allowed_fps:
                return (True, self._keyid(sig))
        return (False, self._keyid(sigs[0]))

    def get_key_repr(self, keyname):
        fingerprint = self._fingerprint(keyname)
        uids = self.gpg.list_keys(keys=fingerprint)[0]['uids']
        fp_formatted = ' '.join([(fingerprint[i:i + 4])
                                for i in range(0, len(fingerprint), 4)])
        uidstr = ' aka '.join([f'"{uid}"' for uid in uids])
        return f'Fingerprint {fp_formatted} from {uidstr}'


class SSHKeyHandler(KeyHandler):
    def __init__(self, workdir, signers, confinst):
        self.workdir = workdir
        self.signers = {}

        for name, loc in signers.items():
            if 'repo' not in loc:
                raise KasUserError('For SSH keys, a repo must be specified')
            if 'path' not in loc:
                raise KasUserError('For SSH keys, a path must be specified')
            repo = confinst.get_repo(loc['repo'])
            pubfile = Path(repo.path) / Path(loc['path'])
            keydata = subprocess.check_output(['ssh-keygen', '-lf',
                                               pubfile.absolute()])
            keyparts = keydata.decode('utf-8').split()
            size, fp = keyparts[0:2]
            comment = ' '.join(keyparts[2:-1])
            rawtype = keyparts[-1].replace('(', '').replace(')', '')
            keytype = self._key_name_from_sn(rawtype, size)
            if 'fingerprint' in loc and loc['fingerprint'] != fp:
                raise KeyImportError(name,
                                     'Fingerprints do not match: '
                                     f'Key has "{fp}". '
                                     f'Expected "{loc["fingerprint"]}".')
            rawkey = subprocess.check_output(['ssh-keygen', '-mRFC4716', '-ef',
                                              pubfile])
            key = self._key_from_rfc4716(rawkey.decode('utf-8'))
            self.signers[name] = {
                'type': keytype.lower(),
                'key': key,
                'comment': comment,
                'fingerprint': fp,
                'size': size
            }

    @staticmethod
    def _key_name_from_sn(name, size):
        """
        Convert the key type and size from the output of ssh-keygen -lf
        to the ssh key type string.
        """
        # RFC 4253 section 6.6
        if name == 'DSA':
            return 'ssh-dss'
        if name == 'RSA':
            return 'ssh-rsa'
        # RFC 5656 section 6.2
        if name == 'ECDSA' and int(size) in [256, 384, 521]:
            return f'ecdsa-sha2-nistp{size}'
        # RFC 8709 section 6
        if name == 'ED25519':
            return 'ssh-ed25519'
        raise KasUserError(f'Unsupported key type "{name}" with size "{size}"')

    @staticmethod
    def _key_from_rfc4716(data):
        parts = []
        for line in data.splitlines():
            if not line.startswith('----') and not line.startswith('Comment:'):
                parts.append(line)
        return ''.join(parts)

    def _keyid(self, fingerprint):
        for k, v in self.signers.items():
            if v['fingerprint'] == fingerprint:
                return k
        return None

    def prepare_validation(self, repo):
        super().prepare_validation(repo)
        trustpath = self.workdir / repo.name
        trustpath.mkdir(exist_ok=True)
        allowedSignersFile = trustpath / 'allowedSigners'

        with open(allowedSignersFile, 'w') as f:
            for k in repo.allowed_signers:
                signer = self.signers.get(k)
                f.write(f'"{signer["comment"]}" namespaces="git" '
                        f'{signer["type"]} {signer["key"]}\n')

        gitconfig = Path(repo.path) / '.git/config'
        with GitConfigParser(gitconfig, read_only=False) as config:
            config.add_section('gpg "ssh"')
            config['gpg "ssh"']['allowedSignersFile'] = str(allowedSignersFile)
            config.write()

    def validate_allowed_signer(self, repo, output):
        super().validate_allowed_signer(repo, output)
        fp = output.split()[-1]
        return (True, self._keyid(fp))

    def get_key_repr(self, keyname):
        signer = self.signers.get(keyname)
        return f'Fingerprint {signer["fingerprint"]} ({signer["type"]}) ' \
               f'from "{signer["comment"]}"'
