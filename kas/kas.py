#!/usr/bin/env python3
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
"""
    This module is the main entry point for kas, setup tool for bitbake based
    projects
"""

import argparse
import atexit
import asyncio
import traceback
import logging
import signal
import sys
import os
import pkg_resources

try:
    import colorlog
    HAVE_COLORLOG = True
except ImportError:
    HAVE_COLORLOG = False

from . import __version__, __file_version__, __compatible_file_version__

# Import kas plugins
# Since they are added by decorators, they don't need to be called,
# just imported.
# pylint: disable=unused-import
from .libkas import kasplugin
from . import build
from . import shell

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017'


def create_logger():
    """
        Setup the logging environment
    """
    log = logging.getLogger()  # root logger
    log.setLevel(logging.INFO)
    format_str = '%(asctime)s - %(levelname)-8s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    if HAVE_COLORLOG and os.isatty(2):
        cformat = '%(log_color)s' + format_str
        colors = {'DEBUG': 'reset',
                  'INFO': 'reset',
                  'WARNING': 'bold_yellow',
                  'ERROR': 'bold_red',
                  'CRITICAL': 'bold_red'}
        formatter = colorlog.ColoredFormatter(cformat, date_format,
                                              log_colors=colors)
    else:
        formatter = logging.Formatter(format_str, date_format)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)
    return logging.getLogger(__name__)


def interruption():
    """
        Ignore SIGINT/SIGTERM in kas, let them be handled by our sub-processes
    """
    pass


def _atexit_handler():
    """
        Wait for completion of the event loop
    """
    loop = asyncio.get_event_loop()
    pending = asyncio.Task.all_tasks()
    loop.run_until_complete(asyncio.gather(*pending))
    loop.close()


def kas_get_argparser():
    """
        Creates a argparser for kas with all plugins.
    """
    parser = argparse.ArgumentParser(description='kas - setup tool for '
                                     'bitbake based project')

    verstr = '%(prog)s {} (configuration format version {}, ' \
        'earliest compatible version {})'.format(__version__, __file_version__,
                                                 __compatible_file_version__)
    parser.add_argument('--version', action='version', version=verstr)

    parser.add_argument('-d', '--debug',
                        action='store_true',
                        help='Enable debug logging')

    subparser = parser.add_subparsers(help='sub command help', dest='cmd')
    for ext_plugin in pkg_resources.iter_entry_points('kas.plugins'):
        ext_plugin.load()

    for plugin in getattr(kasplugin, 'plugins', []):
        plugin.get_argparser(subparser)

    return parser


def kas(argv):
    """
        The main entry point of kas.
    """
    create_logger()

    parser = kas_get_argparser()
    args = parser.parse_args(argv)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info('%s %s started', os.path.basename(sys.argv[0]), __version__)

    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, interruption)
    atexit.register(_atexit_handler)

    for plugin in getattr(kasplugin, 'plugins', []):
        if plugin().run(args):
            return

    parser.print_help()


def main():
    """
        The main function that operates as a wrapper around kas.
    """
    # pylint: disable=broad-except

    try:
        sys.exit(kas(sys.argv[1:]))
    except Exception as err:
        logging.error('%s', err)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
