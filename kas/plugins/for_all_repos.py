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
"""
    This plugin implements the ``kas for-all-repos`` command.

    When this command is executed, kas will checkout the repositories listed
    in the chosen config file and then execute a specified command in each
    repository. It can be used to query the repository status, automate
    actions such as archiving the layers used in a build or to execute any
    other required commands.

    For example, to print the commit hashes used by each repository used in
    the file ``kas-project.yml`` (assuming they are all git repositories) you
    could run::

        kas for-all-repos kas-project.yml 'git rev-parse HEAD'

    The environment for executing the command in each repository is extended
    to include the following variables:

      * ``KAS_REPO_NAME``: The name of the current repository determined by
        either the name property or by the key used for this repo in the config
        file.

      * ``KAS_REPO_PATH``: The path of the local directory where this
        repository is checked out, relative to the directory where ``kas`` is
        executed.

      * ``KAS_REPO_URL``: The URL from which this repository was cloned, or an
        empty string if no remote URL was given in the config file.

      * ``KAS_REPO_REFSPEC``: The refspec which was checked out for this
        repository, or an empty string if no refspec was given in the config
        file.
"""

import logging
import subprocess
from kas.context import create_global_context
from kas.config import Config
from kas.libcmds import Macro, Command

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class ForAllRepos:
    name = 'for-all-repos'
    helpmsg = (
        'Runs a specified command in all checked out repositories.'
    )

    @classmethod
    def setup_parser(cls, parser):
        parser.add_argument('command',
                            help='Command to be executed as a string.')

    def run(self, args):
        ctx = create_global_context(args)
        ctx.config = Config(args.config)

        macro = Macro()
        macro.add(ForAllReposCommand(args.command))
        macro.run(ctx, args.skip)


class ForAllReposCommand(Command):
    def __init__(self, command):
        super().__init__()
        self.command = command

    def __str__(self):
        return 'for-all-repos'

    def execute(self, ctx):
        for repo in ctx.config.get_repos():
            env = {
                **ctx.environ,
                'KAS_REPO_NAME': repo.name,
                'KAS_REPO_PATH': repo.path,
                'KAS_REPO_URL': repo.url or '',
                'KAS_REPO_REFSPEC': repo.refspec or '',
            }
            logging.info('%s$ %s', repo.path, self.command)
            retcode = subprocess.call(self.command, shell=True, cwd=repo.path,
                                      env=env)
            if retcode != 0:
                logging.error('Command failed with return code %d', retcode)


__KAS_PLUGINS__ = [ForAllRepos]
