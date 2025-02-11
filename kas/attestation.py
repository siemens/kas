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
"""
    This module provides infrastructure to generate provenance attestation
    of the build process.
"""

import os
import distro
import logging
import hashlib
import base64
import sys
from enum import Enum
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timezone
from kas import __version__ as KASVERSION


SLSA_PROVENANCE_TYPE = 'https://slsa.dev/provenance/v1'
KAS_BUILDER_ID = 'https://github.com/siemens/kas'
KAS_BUILD_TYPE = 'https://kas.readthedocs.io/en' \
                 f'/{KASVERSION}/userguide/project-configuration.html'
INTOTO_STATEMENT_TYPE = 'https://in-toto.io/Statement/v1'


def date_to_rfc3339(dt):
    return dt.astimezone(timezone.utc) \
             .strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def file_digest_slow(f, algorithm):
    """
        Implementation of hashlib.file_digest for python < 3.11
    """
    hash = hashlib.new(algorithm)
    while True:
        data = f.read()
        if not data:
            break
        hash.update(data)
    return hash


class Provenance:
    """
        Create a build attestation predicate in SLSA provenance format
        for a kas build.
    """
    class Mode(Enum):
        MIN = 1
        MAX = 10

    def __init__(self, ctx, t_started, t_finished, mode=Mode.MIN):
        self._ctx = ctx
        self._t_started = t_started
        self._t_finished = t_finished
        self._mode = mode

    @staticmethod
    def _url_with_protocol(url):
        if url.startswith('git@'):
            return f'ssh://{url}'
        if url.startswith('ssh://'):
            return f'{url}'
        if url.startswith('http://') or url.startswith('https://'):
            return f'{url}'

    @staticmethod
    def _strip_credentials(url):
        """
            Returns the url with all credentials removed (best effort)
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            return url
        parsed = urlparse(url)
        if parsed.username and parsed.password:
            url = url.replace(f'{parsed.username}:{parsed.password}@', '')
        return url

    @staticmethod
    def _get_filetype(f: Path):
        if f.suffix == '.json':
            return 'json'
        return 'yaml'

    def _make_relative_path(self, path: Path):
        top_repo_path = Path(self._ctx.config.handler.get_top_repo_path())
        workdir = Path(self._ctx.kas_work_dir)

        if path.is_relative_to(workdir):
            return path.relative_to(workdir)
        else:
            return path.relative_to(top_repo_path)

    def type_(self):
        return SLSA_PROVENANCE_TYPE

    def as_dict(self):
        res_deps = []
        tracked_repos = []
        for r in self._ctx.config.get_repos():
            if r.operations_disabled:
                if not r.url or not r.revision:
                    continue
            digest = {f'{r.get_type()}Commit': r.revision}
            annotations = {
                'dirty': r.dirty,
                'layers': [str(Path(layer).relative_to(r.path))
                           for layer in r.layers]
            }
            cleanurl = self._strip_credentials(r.url)
            dep = {
                'name': r.name,
                'uri': f'{r.get_type()}+{self._url_with_protocol(cleanurl)}',
                'digest': digest,
                'annotations': annotations
            }
            res_deps.append(dep)
            tracked_repos.append(r)

        # (abspath, relpath)
        config_files = [(Path(c), self._make_relative_path(Path(c)))
                        for c in self._ctx.config.filenames]
        for ca, cr in config_files:
            if any([r.contains_path(cr) for r in tracked_repos]):
                logging.debug(f'Config file {cr} is tracked')
                continue

            with open(ca, 'rb') as f:
                content = f.read()
            rd = {
                'name': str(cr),
                'content': base64.b64encode(content).decode('utf-8'),
                'mediaType': f'application/vnd.kas+{self._get_filetype(ca)}'
            }
            res_deps.append(rd)

        bd = {
            'buildType': KAS_BUILD_TYPE,
            'externalParameters': {
                'command': self._ctx.args.cmd,
                'config': [str(c) for _, c in config_files],
                'target': self._ctx.args.target,
                'task': self._ctx.args.task,
                'extra_bitbake_args': self._ctx.args.extra_bitbake_args,
            },
            'internalParameters': {},
            'resolvedDependencies': res_deps
        }
        if self._mode == self.Mode.MAX:
            bd['internalParameters']['env'] = \
                self._ctx.config.get_environment()
        b_versions = {
            'kas': KASVERSION,
            'distro.name': distro.id(),
            'distro.version': distro.version()
        }

        rd = {
            'builder':
            {
                'id': KAS_BUILDER_ID,
                'version': b_versions
            },
            'metadata': {
                'invocationId': os.environ.get('CI_JOB_URL', ''),
                'startedOn': date_to_rfc3339(self._t_started),
                'finishedOn': date_to_rfc3339(self._t_finished),
            },
            'byproducts': []
        }
        p = {
            'buildDefinition': bd,
            'runDetails': rd
        }
        return p


class Statement:
    """
        Create a statement in in-toto format for a kas build.
    """
    def __init__(self, predicate, ctx, t_started, t_finished):
        self._predicate = predicate
        self._ctx = ctx
        self._t_started = t_started
        self._t_finished = t_finished

    def _check_artifact_timestamp(self, name, path):
        """
            Warn if artifact timestamp is not within the build range.
        """
        logging.debug(f'Found artifact {name}:{path} in build dir')
        fullpath = Path(self._ctx.build_dir) / path
        mtime = datetime.fromtimestamp(fullpath.stat().st_mtime)
        if mtime < self._t_started or mtime > self._t_finished:
            logging.warning(
                f'Artifact {name}:{path.name} mtime {mtime.strftime("%c")}'
                f' not in build range '
                f'[{self._t_started.strftime("%c")} - '
                f'{self._t_finished.strftime("%c")}]')

    def as_dict(self):
        pt = self._predicate.type_()
        pp = self._predicate.as_dict()
        subjects = []
        for n, s in self._ctx.config.get_artifacts(missing_ok=False):
            self._check_artifact_timestamp(n, s)
            fullpath = Path(self._ctx.build_dir) / s
            with open(fullpath, "rb") as f:
                if sys.version_info < (3, 11):
                    digest = file_digest_slow(f, "sha256")
                else:
                    digest = hashlib.file_digest(f, "sha256")
            rd = {
                'name': s.name,
                'digest': {'sha256': digest.hexdigest()}
            }
            subjects.append(rd)
        if len(subjects) == 0:
            logging.warning('Attestation does not contain any artifacts.')
        st = {
            '_type': INTOTO_STATEMENT_TYPE,
            'subject': subjects,
            'predicateType': pt,
            'predicate': pp
        }
        return st
