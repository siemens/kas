# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2026
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
    This module provides the ``kas-container-usage`` directive that extracts
    usage information from the ``kas-container`` script and renders it as RST.

    Usage::

        .. kas-container-usage:: synopsis
        .. kas-container-usage:: options
'''
__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2026'

import os
import re
import subprocess

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx
from typing import Dict, Union


KAS_CONTAINER_SCRIPT = os.path.join(
    os.path.dirname(__file__), '..', '..', 'kas-container')


def _get_help_output():
    """Run kas-container --help and return the raw output."""
    result = subprocess.run(
        [KAS_CONTAINER_SCRIPT, '--help'],
        capture_output=True, text=True, check=True)
    return result.stdout


def _parse_help(text):
    """
    Parse the kas-container --help output into structured sections.

    Returns a dict with:
      - 'usage_lines': list of usage line strings
      - 'commands': list of (name, description) tuples
      - 'options': list of (flags, description) tuples
    """
    sections = re.split(
        r'^(Usage:|Positional arguments:|Optional arguments:)\n?',
        text, flags=re.MULTILINE)

    # Build a mapping of section header to content
    parts = {}
    for i in range(1, len(sections), 2):
        parts[sections[i]] = sections[i + 1]

    return {
        'usage_lines': _parse_usage(parts.get('Usage:', '')),
        'commands': _parse_tabbed_entries(parts.get(
            'Positional arguments:', '')),
        'options': _parse_tabbed_entries(parts.get(
            'Optional arguments:', '')),
    }


def _parse_usage(text):
    """Extract usage lines, strip leading 'kas-container' prefix context."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_tabbed_entries(text):
    """Parse lines of 'key<tab>description' into (key, description) tuples."""
    # Unwrap continuation lines (whitespace-indented lines continuing previous)
    text = re.sub(r'\n\s+\t\t\t', ' ', text)
    entries = []
    for line in text.splitlines():
        match = re.match(r'^([^\t]+?)\t+(.*)$', line)
        if match:
            entries.append((match.group(1), match.group(2)))
    return entries


def _build_synopsis(parsed):
    """Build docutils nodes for the synopsis section."""
    code = nodes.literal_block(text='\n'.join(parsed['usage_lines']))
    code['language'] = 'none'
    return [code]


def _build_options(parsed):
    """Build docutils nodes for the commands and options sections."""
    result = []

    # Definition list for commands
    dlist = nodes.definition_list()
    for name, desc in parsed['commands']:
        item = nodes.definition_list_item()
        term = nodes.term()
        term += nodes.strong(text=name)
        item += term
        defn = nodes.definition()
        defn += nodes.paragraph('', nodes.Text(desc))
        item += defn
        dlist += item
    result.append(dlist)

    return result


def _build_option_list(parsed):
    """Build docutils nodes for the options section."""
    # Option list for options
    olist = nodes.option_list()
    for flags, desc in parsed['options']:
        item = nodes.option_list_item()
        group = nodes.option_group()
        for flag in flags.split(', '):
            opt = nodes.option()
            opt += nodes.option_string(text=flag)
            group += opt
        item += group
        description = nodes.description()
        description += nodes.paragraph('', nodes.Text(desc))
        item += description
        olist += item
    return [olist]


class KasContainerUsageDirective(Directive):
    """
    Directive to include kas-container usage information.

    .. kas-container-usage:: synopsis
    .. kas-container-usage:: options
    """

    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec = {}

    def run(self):
        section = self.arguments[0]
        if section not in ('synopsis', 'commands', 'options'):
            self.state_machine.reporter.error(
                f'Invalid kas-container-usage section: {section}. '
                'Must be "synopsis", "commands", or "options".',
                line=self.lineno)
            return []

        env = self.state.document.settings.env
        env.note_dependency(KAS_CONTAINER_SCRIPT)

        help_output = _get_help_output()
        parsed = _parse_help(help_output)

        if section == 'synopsis':
            return _build_synopsis(parsed)
        elif section == 'commands':
            return _build_options(parsed)
        else:
            return _build_option_list(parsed)


def setup(app: Sphinx) -> Dict[str, Union[bool, str]]:
    app.add_directive('kas-container-usage', KasContainerUsageDirective)

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
        'version': '1.0',
    }
