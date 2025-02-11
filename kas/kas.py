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
    This module is the main entry point for kas, setup tool for bitbake based
    projects. In case of user errors (e.g. invalid configuration, repo fetch
    failure) kas exits with error code 2, while exiting with 1 for internal
    errors. When cancelled by SIGINT, kas exits with 130. For details on error
    handling, see :mod:`kas.kasusererror`.
"""

import argparse
import asyncio
import traceback
import logging
import signal
import sys
import os
from .kasusererror import KasUserError, CommandExecError

try:
    import colorlog
    HAVE_COLORLOG = True
except ImportError:
    HAVE_COLORLOG = False

from . import __version__, __file_version__, __compatible_file_version__
from . import plugins

__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'

DEFAULT_LOG_LEVEL = 'info'


def create_logger():
    """
        Setup the logging environment
    """
    log = logging.getLogger()  # root logger
    log.setLevel(DEFAULT_LOG_LEVEL.upper())
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


def cleanup_logger():
    """
        Cleanup the logging environment
    """
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            logging.root.removeHandler(handler)


def interruption():
    """
        Gracefully cancel all tasks in the event loop
    """
    loop = asyncio.get_event_loop()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.remove_signal_handler(sig)
        loop.add_signal_handler(sig, termination)
    pending = asyncio.all_tasks(loop)
    if pending:
        logging.debug(f'waiting for {len(pending)} tasks to terminate')
    [t.cancel() for t in pending]


def termination():
    """
        Forcefully terminate the process
    """
    logging.error('kas terminated forcefully')
    os._exit(130)


def shutdown_loop(loop):
    """
        Waits for completion of the event loop
    """
    pending = asyncio.all_tasks(loop)
    loop.run_until_complete(asyncio.gather(*pending))
    loop.close()


def kas_get_argparser():
    """
        Creates an argparser for kas with all plugins.
    """

    # Load plugins here so that the commands and arguments introduced by the
    # plugins can be seen by sphinx when it calls this function to build the
    # documentation
    plugins.load()

    parser = argparse.ArgumentParser(description='kas - setup tool for '
                                     'bitbake based project')

    verstr = f'%(prog)s {__version__} ' \
             f'(configuration format version {__file_version__}, ' \
             f'earliest compatible version {__compatible_file_version__})'
    parser.add_argument('--version', action='version', version=verstr)

    parser.add_argument('-l', '--log-level',
                        choices=['debug', 'info', 'warning', 'error',
                                 'critical'],
                        default=f'{DEFAULT_LOG_LEVEL}',
                        help=f'Set log level (default: {DEFAULT_LOG_LEVEL})')

    subparser = parser.add_subparsers(help='sub command help', dest='cmd')

    for plugin in plugins.all():
        plugin_parser = subparser.add_parser(
            plugin.name,
            help=plugin.helpmsg,
            formatter_class=ArgumentChoicesHelpFormatter)
        plugin.setup_parser(plugin_parser)

    return parser


class ArgumentChoicesHelpFormatter(argparse.HelpFormatter):
    """Help message formatter which adds choices to argument help.

    If the default METAVAR is used, this will do nothing, as the default
    METAVAR shows the available choices already. If the METAVAR is
    overridden, and %(choice)s is not present in the help string, add
    them.
    """

    def _get_help_string(self, action):
        help = action.help
        if action.choices and action.metavar is not None:
            if "%(choices)" not in action.help:
                help += " Possible choices: %(choices)s."
        return help


def kas(argv):
    """
        The actual main entry point of kas.
    """
    create_logger()

    parser = kas_get_argparser()
    args = parser.parse_args(argv)

    if args.log_level:
        logging.getLogger().setLevel(args.log_level.upper())

    logging.info('%s %s started', os.path.basename(sys.argv[0]), __version__)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.add_signal_handler(signal.SIGTERM, interruption)
    # don't overwrite pytest's signal handler
    if "PYTEST_CURRENT_TEST" not in os.environ:
        loop.add_signal_handler(signal.SIGINT, interruption)

    try:
        plugin_class = plugins.get(args.cmd)
        if plugin_class:
            plugin = plugin_class()
            plugin.run(args)
        else:
            parser.print_help()
    except CommandExecError as err:
        logging.error('%s', err)
        raise
    except KasUserError as err:
        logging.error('%s', err)
        raise
    except asyncio.CancelledError:
        logging.error('kas execution cancelled')
        raise
    except Exception as err:
        logging.error('%s', err)
        raise
    finally:
        shutdown_loop(loop)
        cleanup_logger()


def main():
    """
        The main function that operates as a wrapper around kas.
    """

    try:
        kas(sys.argv[1:])
    except CommandExecError as err:
        sys.exit(err.ret_code if err.forward else 2)
    except KasUserError:
        sys.exit(2)
    except asyncio.CancelledError:
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
