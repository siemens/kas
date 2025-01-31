# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2020
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
    This module contains the schema of the configuration file.
'''
__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2024'

import json
import os


def _load_schema():
    global CONFIGSCHEMA
    global __file_version__
    global __compatible_file_version__
    global __schema_definition__

    cwd = os.path.dirname(os.path.realpath(__file__))
    __schema_definition__ = os.path.join(cwd, 'schema-kas.json')
    with open(__schema_definition__, 'r') as f:
        CONFIGSCHEMA = json.load(f)
        header_node = CONFIGSCHEMA['properties']['header']
        version_node = header_node['properties']['version']['anyOf'][1]
        __file_version__ = version_node["maximum"]
        __compatible_file_version__ = version_node["minimum"]


_load_schema()
