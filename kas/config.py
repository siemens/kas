# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2021
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
    This module contains the implementation of the kas configuration.
"""

import os
import json
import copy
from pathlib import Path
from .repos import Repo
from .includehandler import IncludeHandler
from .kasusererror import ArtifactNotFoundError
from .configschema import CONFIGSCHEMA

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2021'

CONFIG_YAML_FILE = '.config.yaml'


class Config:
    """
        Implements the kas configuration based on config files.
    """
    def __init__(self, ctx, filename, target=None, task=None):
        self._override_target = target
        self._override_task = task
        self._build_dir = ctx.build_dir
        self.__config = {}
        if not filename:
            filename = os.path.join(ctx.kas_work_dir, CONFIG_YAML_FILE)

        self.filenames = [os.path.abspath(configfile)
                          for configfile in filename.split(':')]

        update = ctx.args.update if hasattr(ctx.args, 'update') else False

        self.handler = IncludeHandler(self.filenames, not update)
        self.repo_dict = {}
        self.repo_cfg_hashes = {}

    @property
    def _config(self):
        if not self.__config:
            raise RuntimeError("Config has not been imported yet.")
        return self.__config

    def get_build_system(self):
        """
            Returns the pre-selected build system
        """
        return self._config.get('build_system', '')

    def find_missing_repos(self, repo_paths={}):
        """
            Returns repos that are in config but not on disk and updates
            the internal config dictionary.
        """
        (self.__config, missing_repo_names) = \
            self.handler.get_config(repos=repo_paths)

        return missing_repo_names

    def get_config(self, remove_includes=False, apply_overrides=False):
        """
            Returns a copy of the config dict
        """
        config = copy.deepcopy(self._config)
        if remove_includes and 'includes' in config['header']:
            del config['header']['includes']
        if apply_overrides:
            overrides = config.get('overrides', {})
            if overrides:
                config.update(overrides)
                del config['overrides']
        return config

    def get_lockfiles(self):
        """
            Returns the list of in-use lockfiles.
        """
        return self.handler.get_lockfiles()

    def get_repos_config(self):
        """
            Returns the repository configuration
        """
        return self._config.get('repos', {})

    def get_repos(self):
        """
            Returns the list of repos.
        """

        # Always keep repo_dict and repos synchronous
        # when calling get_repos
        self.repo_dict = self._get_repo_dict()
        return list(self.repo_dict.values())

    def get_repo(self, name):
        """
            Returns a `Repo` instance for the configuration with the key
            `name`.
        """
        repo_defaults = self._config.get('defaults', {}).get('repos', {})
        overrides = self._config.get('overrides', {}) \
                                .get('repos', {}).get(name, {})
        config = self.get_repos_config()[name] or {}
        top_repo_path = self.handler.get_top_repo_path()

        # Check if we have this repo with an identical config already.
        # As this function is called across various places and with different
        # configurations (e.g. due to updates from transitive includes),
        # we cache the results.
        args = (name, config, repo_defaults, top_repo_path, overrides)
        return self._get_or_create_repo(args)

    def _get_or_create_repo(self, args):
        """
            Get a repo from the cache and insert it if not existing.
            Creating repos is expensive due to external commands being called.
        """
        encoded = json.dumps(args, sort_keys=True).encode()
        if encoded in self.repo_cfg_hashes:
            return self.repo_cfg_hashes[encoded]
        repo = Repo.factory(*args)
        self.repo_cfg_hashes[encoded] = repo
        return repo

    def _get_repo_dict(self):
        """
            Returns a dictionary containing the repositories with
            their names (as it is defined in the config file) as keys
            and the `Repo` instances as values.
        """
        return {name: self.get_repo(name) for name in self.get_repos_config()}

    def get_bitbake_targets(self):
        """
            Returns a list of bitbake targets
        """
        if self._override_target:
            return self._override_target
        environ_targets = [i
                           for i in os.environ.get('KAS_TARGET', '').split()
                           if i]
        if environ_targets:
            return environ_targets
        def_target = CONFIGSCHEMA['properties']['target']['default']
        target = self._config.get('target', def_target)
        if isinstance(target, str):
            return [target]
        return target

    def get_bitbake_task(self):
        """
            Returns the bitbake task
        """
        if self._override_task:
            return self._override_task
        default = CONFIGSCHEMA['properties']['task']['default']
        return os.environ.get('KAS_TASK',
                              self._config.get('task', default))

    def _get_conf_header(self, header_name):
        """
            Returns the local.conf header
        """
        header = ''
        for key, value in sorted(self._config.get(header_name, {}).items()):
            header += f'# {key}\n{value}\n'
        return header

    def get_bblayers_conf_header(self):
        """
            Returns the bblayers.conf header
        """
        return self._get_conf_header('bblayers_conf_header')

    def get_local_conf_header(self):
        """
            Returns the local.conf header
        """
        return self._get_conf_header('local_conf_header')

    def get_machine(self):
        """
            Returns the machine
        """
        default = CONFIGSCHEMA['properties']['machine']['default']
        return os.environ.get('KAS_MACHINE',
                              self._config.get('machine', default))

    def get_distro(self):
        """
            Returns the distro
        """
        default = CONFIGSCHEMA['properties']['distro']['default']
        return os.environ.get('KAS_DISTRO',
                              self._config.get('distro', default))

    def get_environment(self):
        """
            Returns the configured environment variables from the configuration
            file with possible overwritten values from the environment.
        """
        env = self._config.get('env', {})
        return {var: os.environ.get(var, env[var]) for var in env}

    def get_multiconfig(self):
        """
            Returns the multiconfig array as bitbake string
        """
        multiconfigs = set()
        for target in self.get_bitbake_targets():
            if target.startswith('multiconfig:') or target.startswith('mc:'):
                multiconfigs.add(target.split(':')[1])
        return ' '.join(multiconfigs)

    def get_artifacts(self, missing_ok=True):
        """
            Returns the found artifacts after glob expansion, relative
            to the build_dir as a list of tuples (name, path).
            If missing_ok=False, raises an ArtifactNotFoundError if no
            artifact for a given name is found.
        """
        arts = self._config.get('artifacts', {})
        foundfiles = []
        for name, art in arts.items():
            files = list(Path(self._build_dir).glob(art))
            if not missing_ok and len(files) == 0:
                raise ArtifactNotFoundError(name, art)
            foundfiles.extend([(name, f) for f in files])
        return [(n, f.relative_to(self._build_dir))
                for n, f in foundfiles]

    def get_signers_config(self, keytype=None):
        """
            Returns the keys from the configuration
        """
        signers = self._config.get('signers', {})
        if not keytype:
            return signers
        else:
            return {k: v for k, v in signers.items()
                    if v.get('type', 'gpg') == keytype}
