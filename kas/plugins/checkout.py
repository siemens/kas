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
    This plugin implements the ``kas checkout`` command.

    When this command is executed, kas will checkout repositories and set up
    the build directory as specified in the chosen config file. This command
    is useful if you need to inspect the configuration or modify any of the
    checked out layers before starting a build.

    For example, to setup the configuration described in the file
    ``kas-project.yml`` you could run::

        kas checkout kas-project.yml
"""

from kas.context import create_global_context
from kas.config import Config
from kas.libcmds import Macro

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'


class Checkout:
    name = 'checkout'
    helpmsg = (
        'Checks out all necessary repositories and sets up the build '
        'directory as specified in the configuration file.'
    )

    @classmethod
    def setup_parser(cls, parser):
        pass

    def run(self, args):
        ctx = create_global_context(args)
        ctx.config = Config(args.config)

        macro = Macro()
        macro.run(ctx, args.skip)


__KAS_PLUGINS__ = [Checkout]
