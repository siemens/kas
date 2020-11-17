# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2018
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
    This module contains and manages kas plugins
"""

PLUGINS = {}


def register_plugins(mod):
    """
        Register all kas plugins found in a module
    """
    for plugin in getattr(mod, '__KAS_PLUGINS__', []):
        PLUGINS[plugin.name] = plugin


def load():
    """
        Import all kas plugins
    """
    from . import build
    from . import for_all_repos
    from . import checkout
    from . import shell

    register_plugins(build)
    register_plugins(checkout)
    register_plugins(for_all_repos)
    register_plugins(shell)


def get(name):
    """
        Lookup a kas plugin class by name
    """
    return PLUGINS.get(name, None)


def all():
    """
        Get a list of all loaded kas plugin classes
    """
    return PLUGINS.values()
