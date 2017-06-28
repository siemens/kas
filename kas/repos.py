# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017
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
    This module contains the Repo class.
"""

import os
from urllib.parse import urlparse

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class Repo:
    """
        Represents a repository in the kas configuration.
    """

    def __init__(self, url, path, refspec=None, layers=None):
        self.url = url
        self.path = path
        self.refspec = refspec
        self._layers = layers
        self.name = os.path.basename(self.path)
        self.git_operation_disabled = False

    def disable_git_operations(self):
        """
            Disabled all git operation for this repository.
        """
        self.git_operation_disabled = True

    def __getattr__(self, item):
        if item == 'layers':
            if not self._layers:
                return [self.path]
            return [self.path + '/' + l for l in self._layers]
        elif item == 'qualified_name':
            url = urlparse(self.url)
            return ('{url.netloc}{url.path}'
                    .format(url=url)
                    .replace('@', '.')
                    .replace(':', '.')
                    .replace('/', '.')
                    .replace('*', '.'))

    def __str__(self):
        return '%s:%s %s %s' % (self.url, self.refspec,
                                self.path, self._layers)
