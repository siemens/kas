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

import codecs
import os
from configparser import SafeConfigParser

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


class KasState:
    def __init__(self):
        self.filename = os.path.join(os.environ.get('XDG_CONFIG_HOME',
                                                    os.path.expandvars('$HOME/.config')),
                                     os.path.join('kas', 'kasstate.ini'))
        self.parser = SafeConfigParser()
        try:
            with codecs.open(self.filename, 'r', encoding='utf-8') as f:
                self.parser.readfp(f)
        except:
            pass

    def __del__(self):
        if not os.path.exists(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
        with codecs.open(self.filename, 'w', encoding='utf-8') as f:
            self.parser.write(f)

    def get_option(self, section, option, default):
        if not self.parser.has_option(section, option):
            self.set_option(section, option, default)
        return self.parser.get(section, option)

    def set_option(self, section, option, value):
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, option, value)
