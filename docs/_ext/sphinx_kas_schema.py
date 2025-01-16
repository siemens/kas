# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2024
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
    This module contains the :kasschemadesc:`<node>` role to extract the
    description of a node from the schema. The `<node>` hereby is a path
    to the node in the schema, separated by dots. For example, the
    header.version node can be accessed with
    :kasschemadesc:`header.properties.version`.
'''
__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2024'

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxRole
from docutils.parsers.rst.states import Struct
from sphinx.util.nodes import nodes
from typing import Dict, Union
import re
from kas.configschema import CONFIGSCHEMA, __schema_definition__


class KasSchemaDescRole(SphinxRole):

    required_arguments = 1

    def __init__(self):
        super().__init__()
        self.key_regex = re.compile(r'([a-zA-Z_]+)(?:\[(\d+)\])?')

    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        messages = []
        node = CONFIGSCHEMA['properties']
        path = self.text.split('.')
        self.env.note_dependency(__schema_definition__)
        try:
            for part in path:
                match = self.key_regex.match(part).groups()
                if match[1]:
                    node = node[match[0]][int(match[1])]
                elif match[0]:
                    node = node[match[0]]
                else:
                    raise KeyError
        except KeyError:
            messages.append(self.inliner.document.reporter.error(
                f'Invalid path: {self.text}',
                line=self.lineno,
            ))
            return [], messages
        try:
            desc = node['description']
        except KeyError:
            messages.append(self.inliner.document.reporter.error(
                f'Description missing for path: {self.text}',
                line=self.lineno,
            ))
            return [], messages
        default = node.get('default', None)
        allowed_values = node.get('enum', None)

        memo = Struct(document=self.inliner.document,
                      reporter=self.inliner.reporter,
                      language=self.inliner.language)
        parent = nodes.paragraph()
        processed, msgs = self.inliner.parse(desc, self.lineno, memo, parent)
        parent += processed
        messages += msgs
        if default:
            def_pg = nodes.paragraph()
            def_pg += nodes.strong(text='Default: ')
            def_pg += nodes.literal(text=default)
            parent += def_pg
        if allowed_values:
            av_pg = nodes.paragraph()
            av_pg += nodes.strong(text='Supported values: ')
            for i in range(len(allowed_values)):
                if i != 0:
                    av_pg += nodes.Text(', ')
                av_pg += nodes.literal(text=allowed_values[i])
            parent += av_pg

        return parent, messages


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    app.add_role('kasschemadesc', KasSchemaDescRole())

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        'version': '1.0',
    }
