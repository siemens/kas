#!/usr/bin/env python
#
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

import argparse
import traceback
import logging
import sys
import os
import pkg_resources

try:
    import colorlog
    have_colorlog = True
except ImportError:
    have_colorlog = False

from .build import Build
from .shell import Shell
from .__version__ import __version__

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


def create_logger():
    log = logging.getLogger()  # root logger
    log.setLevel(logging.INFO)
    format = '%(asctime)s - %(levelname)-8s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    if have_colorlog and os.isatty(2):
        cformat = '%(log_color)s' + format
        colors = {'DEBUG': 'reset',
                  'INFO': 'reset',
                  'WARNING': 'bold_yellow',
                  'ERROR': 'bold_red',
                  'CRITICAL': 'bold_red'}
        f = colorlog.ColoredFormatter(cformat, date_format, log_colors=colors)
    else:
        f = logging.Formatter(format, date_format)
    ch = logging.StreamHandler()
    ch.setFormatter(f)
    log.addHandler(ch)
    return logging.getLogger(__name__)


def kas(argv):
    create_logger()

    parser = argparse.ArgumentParser(description='Steer ebs-yocto builds')

    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debug logging')

    subparser = parser.add_subparsers(help='sub command help', dest='cmd')
    sub_cmds = [Build(subparser), Shell(subparser)]

    for plugin in pkg_resources.iter_entry_points('kas.plugins'):
        cmd = plugin.load()
        sub_cmds.append(cmd(subparser))

    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    for cmd in sub_cmds:
        if cmd.run(args):
            return

    parser.print_help()


def main():
    try:
        sys.exit(kas(sys.argv[1:]))
    except Exception as err:
        logging.error('%s' % err)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
