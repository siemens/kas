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
    This module implements how includes of configuration files are handled in
    kas.
"""

import os
from pathlib import Path
from collections import OrderedDict
from collections.abc import Mapping
from functools import cached_property
import functools
import logging
import json
import yaml

from jsonschema.validators import validator_for

from .kasusererror import KasUserError
from .repos import Repo
from . import __file_version__, __compatible_file_version__, __version__
from . import CONFIGSCHEMA

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2021'

SOURCE_DIR_OVERRIDE_KEY = '_source_dir'
SOURCE_DIR_HOST_OVERRIDE_KEY = '_source_dir_host'
PROJECT_CONFIG_URL = f'https://kas.readthedocs.io/en/{__version__}/' \
    'userguide/project-configuration.html'


class LoadConfigException(KasUserError):
    """
        Class for exceptions that appear while loading a configuration file.
    """
    def __init__(self, message, filename):
        super().__init__(f'{message}: {filename}')


class IncludeException(KasUserError):
    """
        Class for exceptions that appear in the include mechanism.
    """
    pass


class ConfigFile():
    def __init__(self, filename, is_external, is_lockfile):
        self.filename = Path(filename)
        self.config = {}
        # src_dir must only be set by auto-generated config file
        self.src_dir = None
        self.is_external = is_external
        self.is_lockfile = is_lockfile

    @staticmethod
    def load(filename, is_external=False, is_lockfile=False):
        """
            Load the configuration file and test if version is supported.
        """
        cf = ConfigFile(filename, is_external, is_lockfile)
        (_, ext) = os.path.splitext(filename)
        if ext == '.json':
            with open(filename, 'rb') as fds:
                cf.config = json.load(fds)
        elif ext in ['.yml', '.yaml']:
            try:
                with open(filename, 'rb') as fds:
                    cf.config = yaml.safe_load(fds)
            except yaml.YAMLError as e:
                msg = f'Error in line {e.problem_mark.line + 1}' \
                    if hasattr(e, 'problem_mark') else ''
                raise LoadConfigException(
                    f'Configuration file is not valid YAML: {msg}',
                    filename)
        else:
            raise LoadConfigException('Config file extension not recognized',
                                      filename)

        validator_class = validator_for(CONFIGSCHEMA)
        validator = validator_class(CONFIGSCHEMA)
        validation_error = False

        for error in sorted(validator.iter_errors(cf.config), key=str):
            validation_error = True
            logging.error('Config file validation Error:\n%s', error.message)
            logging.error('For a list of supported configuration elements, '
                          'see %s', PROJECT_CONFIG_URL)
            logging.debug('Validation against this schema failed:\n%s',
                          json.dumps(error.schema, indent=2))

        if validation_error:
            raise LoadConfigException('Error(s) occured while validating the '
                                      'config file', filename)

        try:
            version_value = int(cf.config['header']['version'])
        except ValueError:
            # Be compatible: version string '0.10' is equivalent to file
            # version 1 This check is already done in the config schema so
            # here just set the right version
            version_value = 1

        if version_value < __compatible_file_version__ or \
           version_value > __file_version__:
            raise LoadConfigException('This version of kas is compatible with '
                                      f'version {__compatible_file_version__} '
                                      f'to {__file_version__}, '
                                      f'file has version {version_value}',
                                      filename)

        if cf.config.get('proxy_config'):
            logging.warning('Obsolete ''proxy_config'' detected. '
                            'This has no effect and will be rejected soon.')

        cf.src_dir = cf.config.get(SOURCE_DIR_OVERRIDE_KEY, None)
        return cf


class IncludeHandler:
    """
        Implements a handler where every configuration file should
        contain a dictionary as the base type with and 'includes'
        key containing a list of includes.

        The includes can be specified in two ways: as a string
        containing the path, relative to the repository root from the
        current file, or as a dictionary. The dictionary must have a
        'file' key containing the path to the include file and a 'repo'
        key containing the key of the repository. The path is interpreted
        relative to the repository root path, which is lazy resolved by
        the first access of a method.

        The includes are read and merged from the deepest level upwards.

        In case ``use_lock`` is ``True``, kas checks if a file
        ``<file>.lock.<ext>`` exists next to the first entry in
        ``top_files``. This filename is then appended to the list of
        ``top_files``.
    """

    def __init__(self, top_files, use_lock=True):
        self.top_files = top_files
        self.use_lock = use_lock
        self.config_files = []

    def get_lock_filename(self, kasfile=None):
        """
        Returns the lockfile name for the given kas config file.
        """
        file = Path(kasfile or self.top_files[0])
        return file.parent / (file.stem + '.lock' + file.suffix)

    @cached_property
    def top_repo_path(self):
        """
        Lazy resolve top repo path as we might need a prepared environment
        """
        return Repo.get_root_path(os.path.dirname(self.top_files[0]))

    def get_lockfiles(self):
        """
        Returns a list of lockfiles in the order the configuration
        files were parsed.
        """
        return list(filter(lambda x: x.is_lockfile, self.config_files))

    def get_top_repo_path(self):
        return self.top_repo_path

    def ensure_from_same_repo(self):
        """
        Ensure that all concatenated config files belong to the same repository
        """
        repo_paths = [Repo.get_root_path(os.path.dirname(configfile),
                                         fallback=False)
                      for configfile in self.top_files]

        if len(set(repo_paths)) > 1:
            raise IncludeException('All concatenated config files must '
                                   'belong to the same repository or all '
                                   'must be outside of versioning control')

    def get_config(self, repos=None):
        """
        Parameters:
          repos -- A dictionary that maps repo names to directory paths

        Returns:
          (config, repos)
            config -- A dictionary containing the configuration
            repos -- A list of missing repo names that are needed \
                     to create a complete configuration
        """

        repos = repos or {}

        def _internal_include_handler(filename, repo_path,
                                      is_external=False, is_lockfile=False):
            """
            Recursively loads include files and finds missing repos.

            Includes are done in the following way:

            topfile.yml:
            -------
            header:
              includes:
                - include1.yml
                - repo: repo1
                  file: include-repo1.yml
                - repo: repo2
                  file: include-repo2.yml
                - include3.yml
            -------

            Includes are merged in in this order:
            ['include1.yml', 'include2.yml', 'include-repo1.yml',
             'include-repo2.yml', 'include-repo2.yml', 'topfile.yml']
            On conflict the latter includes overwrite previous ones and
            the current file overwrites every include. (evaluation depth first
            and from top to bottom)
            """

            missing_repos = []
            configs = []
            try:
                current_config = \
                    ConfigFile.load(filename, is_external, is_lockfile)
                # if lockfile exists, inject it after current file
                lockfile = self.get_lock_filename(filename)
                if Path(lockfile).exists():
                    (cfg, rep) = _internal_include_handler(
                        lockfile,
                        repo_path,
                        is_external=is_external,
                        is_lockfile=True
                    )
                    configs.extend(cfg)
                    missing_repos.extend(rep)
                # src_dir must only be set by auto-generated config file
                if current_config.src_dir:
                    self.top_repo_path = current_config.src_dir
                    repo_path = current_config.src_dir

            except FileNotFoundError:
                raise LoadConfigException('Configuration file not found',
                                          filename)
            if not isinstance(current_config.config, Mapping):
                raise IncludeException('Configuration file does not contain a '
                                       'dictionary as base type')
            header = current_config.config.get('header', {})

            for include in header.get('includes', []):
                if isinstance(include, str):
                    includefile = ''
                    if include.startswith(os.path.pathsep):
                        includefile = include
                    else:
                        includefile = os.path.abspath(
                            os.path.join(repo_path, include))
                        if not os.path.exists(includefile):
                            alternate = os.path.abspath(
                                os.path.join(
                                    os.path.dirname(current_config.filename),
                                    include
                                )
                            )
                            if os.path.exists(alternate):
                                logging.warning(
                                    'Falling back to file-relative addressing '
                                    'of local include "%s"', include)
                                logging.warning(
                                    'Update your layer to repo-relative '
                                    'addressing to avoid this warning')
                                includefile = alternate
                    (cfg, rep) = _internal_include_handler(
                        includefile,
                        repo_path,
                        is_external=is_external
                    )
                    configs.extend(cfg)
                    missing_repos.extend(rep)
                elif isinstance(include, Mapping):
                    includerepo = include.get('repo', None)
                    includedir = repos.get(includerepo, None)
                    if includedir is not None:
                        incexternal = bool(includedir != self.top_repo_path)
                        try:
                            includefile = include['file']
                        except KeyError:
                            raise IncludeException(
                                f'"file" is not specified: {include}')
                        abs_includedir = os.path.abspath(includedir)
                        (cfg, rep) = _internal_include_handler(
                            os.path.join(abs_includedir, includefile),
                            abs_includedir, is_external=incexternal)
                        configs.extend(cfg)
                        missing_repos.extend(rep)
                    else:
                        missing_repos.append(includerepo)
            logging.debug('config file %s (%s)', current_config.filename,
                          'external' if is_external else 'internal')
            configs.append(current_config)
            # Remove all possible duplicates in missing_repos
            missing_repos = list(OrderedDict.fromkeys(missing_repos))
            return (configs, missing_repos)

        def _internal_dict_merge(dest, upd):
            """
            Merges upd recursively into a copy of dest. The order is preserved
            as in the original dict as dict-insertion orders are preserved from
            Python 3.6 onwards.

            If keys in upd intersect with keys in dest we will do a manual
            merge (helpful for non-dict types like FunctionWrapper).
            """
            if (not isinstance(dest, Mapping)) \
                    or (not isinstance(upd, Mapping)):
                raise IncludeException('Cannot merge using non-dict')
            dest = dest.copy()
            updkeys = list(upd.keys())
            if set(list(dest.keys())) & set(updkeys):
                for key in updkeys:
                    val = upd[key]
                    try:
                        dest_subkey = dest.get(key, None)
                    except AttributeError:
                        dest_subkey = None
                    if isinstance(dest_subkey, Mapping) \
                            and isinstance(val, Mapping):
                        ret = _internal_dict_merge(dest_subkey, val)
                        dest[key] = ret
                    else:
                        dest[key] = upd[key]
                return dest
            try:
                for k in upd:
                    dest[k] = upd[k]
            except AttributeError:
                # this mapping is not a dict
                for k in upd:
                    dest[k] = upd[k]
            return dest

        self.config_files = []
        missing_repos = []
        self.ensure_from_same_repo()
        for configfile in self.top_files:
            cfgs, reps = _internal_include_handler(configfile,
                                                   self.get_top_repo_path())
            self.config_files.extend(cfgs)
            for repo in reps:
                if repo not in missing_repos:
                    missing_repos.append(repo)

        config_files = self.config_files
        if not self.use_lock:
            config_files = [x for x in config_files if not x.is_lockfile]

        config = functools.reduce(_internal_dict_merge,
                                  map(lambda x: x.config, config_files))
        # the merged config must have the highest (used) version number
        header_version = max([int(cfg.config['header']['version'])
                              for cfg in config_files])
        config['header']['version'] = header_version
        return config, missing_repos
