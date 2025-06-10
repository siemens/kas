# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2021
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
#
# Parts of this were based on kconfiglib, examples/menuconfig_example.py
#
# Copyright (c) 2011-2019, Ulf Magnusson <ulfalizer@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
"""
    This plugin implements the ``kas menu`` command.

    When this command is executed, kas will open a configuration menu as
    described by a Kconfig file. It processes any pre-existing configuration
    file with saved settings, stores the final selections and invokes the build
    plugin if requested by the user.

    To make use of this plugin, a ``Kconfig`` file has to be provided. The
    menu can define these types of configuration variables that the plugin
    will translate into a kas configuration:

     - kas configuration files that will be included when building the
       generated configuration. Those are picked up from Kconfig string
       variables that have the name prefix ``KAS_INCLUDE_``.

     - bitbake targets that shall be built via the generated configuration.
       Those are picked up from Kconfig string variables that have the name
       prefix ``KAS_TARGET_``.

     - The ``build_system`` that will used. The static Kconfig string variable
       ``KAS_BUILD_SYSTEM`` defines this value which must be ``openembedded``,
       ``oe`` or ``isar`` is set.

     - bitbake configuration variables that will be added to the
       ``local_conf_header`` section of the generated configuration. All other
       active Kconfig string, integer or hex variables are treated as such.

    See https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html
    for a complete documentation of the Kconfig language.

    The menu plugin writes the selected configuration to a ``.config.yaml``
    file in the kas work directory and also reads previous selection from such
    a file if it exists. The ``.config.yaml`` both contains the selected
    configuration in the ``menu_configuration`` key and also the effective
    settings that can be used to invoke ``kas build`` or other kas commands.
"""

import logging
import os
import pprint
import yaml
from kas import __version__, __file_version__
from kas.context import create_global_context
from kas.config import CONFIG_YAML_FILE
from kas.repos import Repo
from kas.includehandler import ConfigFile, \
    SOURCE_DIR_OVERRIDE_KEY, SOURCE_DIR_HOST_OVERRIDE_KEY
from kas.plugins.build import Build
from kas.kasusererror import KasUserError, MissingModuleError

try:
    from kconfiglib import Kconfig, Symbol, Choice, KconfigError, \
        expr_value, TYPE_TO_STR, MENU, COMMENT, STRING, BOOL, INT, HEX, UNKNOWN
    HAVE_KCONFIGLIB = True
except ImportError:
    HAVE_KCONFIGLIB = False  # will be reported in run()

try:
    from snack import SnackScreen, EntryWindow, ButtonChoiceWindow, \
        ButtonBar, Listbox, GridFormHelp
    HAVE_NEWT = True
except ImportError:
    HAVE_NEWT = False  # will be reported in run()

__license__ = 'MIT'
__copyright__ = \
    'Copyright (c) 2011-2019, Ulf Magnusson <ulfalizer@gmail.com>\n' \
    'Copyright (c) Siemens AG, 2021-2023'

SOURCE_DIR_HOST_ENV_KEY = '_KAS_REPO_DIR_HOST'


class VariableTypeError(KasUserError):
    pass


class KConfigLoadError(KasUserError):
    """
    The KConfig file could not be found or is invalid
    """
    pass


def check_sym_is_string(sym):
    if sym.type != STRING:
        raise VariableTypeError(f'Variable {sym.name} must be of string type')


def str_representer(dumper, data):
    style = '|' if len(data.splitlines()) > 1 else None
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


class Args:
    pass


class Menu:
    """
        This class implements the menu plugin for kas.
    """

    name = 'menu'
    helpmsg = (
        'Provides a configuration menu and triggers the build of the choices.'
    )

    @classmethod
    def setup_parser(cls, parser):
        parser.add_argument('kconfig',
                            help='Kconfig file',
                            nargs='?', default='Kconfig')

    def load_config(self, filename):
        try:
            config = ConfigFile.load(filename)
            self.orig_config = config.config
        except FileNotFoundError:
            self.orig_config = {}
            return

        menu_configuration = self.orig_config.get('menu_configuration', {})
        for symname in menu_configuration:
            sym = self.kconf.syms.get(symname)
            if not sym:
                logging.warning(
                    'Ignoring unknown configuration variable %s in %s',
                    symname, filename)
                continue
            symvalue = menu_configuration[symname]
            if sym.type == BOOL:
                sym.set_value('y' if symvalue else 'n')
            elif sym.type == INT:
                sym.set_value(str(symvalue))
            elif sym.type == HEX:
                sym.set_value(str(hex(symvalue)))
            else:  # string
                sym.set_value(symvalue)

    def save_config(self, filename, top_repo_dir):
        kas_includes = []
        kas_targets = []
        kas_build_system = None
        kas_vars = {}
        menu_configuration = {}

        for symname in self.kconf.syms:
            if symname == 'MODULES':
                continue

            sym = self.kconf.syms[symname]
            symvalue = sym.str_value

            if expr_value(sym.direct_dep) < 2:
                continue

            if sym.visibility == 2:
                if sym.type == BOOL:
                    menu_configuration[symname] = symvalue == 'y'
                elif sym.type == STRING:
                    menu_configuration[symname] = symvalue
                elif sym.type == INT:
                    menu_configuration[symname] = int(symvalue)
                elif sym.type == HEX:
                    menu_configuration[symname] = int(symvalue, 16)
                else:
                    raise VariableTypeError(
                        'Configuration variable {symname} uses unsupported '
                        'type')

            if symname.startswith('KAS_INCLUDE_'):
                check_sym_is_string(sym)
                if symvalue != '':
                    kas_includes.append(symvalue)
            elif symname.startswith('KAS_TARGET_'):
                check_sym_is_string(sym)
                if symvalue != '':
                    kas_targets.append(symvalue)
            elif symname == 'KAS_BUILD_SYSTEM':
                check_sym_is_string(sym)
                if symvalue != '':
                    kas_build_system = symvalue
            elif sym.type in (STRING, INT, HEX):
                kas_vars[symname] = symvalue

        config = {
            'header': {
                'version': __file_version__,
                'includes': kas_includes
            },
            'menu_configuration': menu_configuration,
            SOURCE_DIR_OVERRIDE_KEY: top_repo_dir
        }

        if SOURCE_DIR_HOST_ENV_KEY in os.environ:
            config[SOURCE_DIR_HOST_OVERRIDE_KEY] = \
                os.environ[SOURCE_DIR_HOST_ENV_KEY]
        if kas_build_system:
            config['build_system'] = kas_build_system
        if len(kas_targets) > 0:
            config['target'] = kas_targets
        if len(kas_vars) > 0:
            config['local_conf_header'] = {
                '__menu_config_vars': '\n'.join([
                    f'{key} = "{value}"'
                    for key, value in kas_vars.items()
                ])
            }

        logging.debug('Menu configuration:\n%s', pprint.pformat(config))

        if config != self.orig_config:
            logging.info('Saving configuration as %s', filename)

            # format multi-line strings more nicely
            yaml.add_representer(str, str_representer)

            try:
                os.rename(filename, filename + '.old')
            except FileNotFoundError:
                pass

            with open(filename, 'w') as config_file:
                config_file.write(
                    '#\n'
                    f'# Automatically generated by kas {__version__}\n'
                    '#\n')
                yaml.dump(config, config_file)

    def dump_kconf_warnings(self):
        if len(self.kconf.warnings) > 0:
            logging.warning("\n".join(self.kconf.warnings))
            self.kconf.warnings = []

    def run(self, args):
        if not HAVE_KCONFIGLIB:
            raise MissingModuleError('python3-kconfiglib', 'Menu plugin')
        if not HAVE_NEWT:
            raise MissingModuleError('python3-newt', 'Menu plugin')

        ctx = create_global_context(args)

        kconfig_file = os.path.abspath(args.kconfig)
        try:
            self.kconf = Kconfig(kconfig_file, warn_to_stderr=False)
        except (KconfigError, FileNotFoundError) as err:
            raise KConfigLoadError(str(err))

        top_repo_path = Repo.get_root_path(os.path.dirname(kconfig_file))
        config_filename = os.path.join(ctx.kas_work_dir, CONFIG_YAML_FILE)

        self.load_config(config_filename)
        self.dump_kconf_warnings()

        menu = Menuconfig(self.kconf)
        action = menu.show()

        if action == 'exit':
            return

        self.save_config(config_filename, top_repo_path)
        self.dump_kconf_warnings()

        if action == 'build':
            logging.debug('Starting build')

            build_args = Args()
            build_args.config = None
            build_args.target = None
            build_args.task = None
            build_args.extra_bitbake_args = []
            build_args.skip = None
            build_args.provenance = False

            Build().run(build_args)


class Menuconfig():
    def __init__(self, kconf):
        self.kconf = kconf
        self.screen = None

    @staticmethod
    def value_str(sym):
        """
        Returns the value part ("[*]", "(foo)" etc.) of a menu entry.
        """
        if sym.type in (STRING, INT, HEX):
            return f"({sym.str_value})"

        # BOOL (TRISTATE not supported)

        # The choice mode is an upper bound on the visibility of choice
        # symbols, so we can check the choice symbols' own visibility to see
        # if the choice is in y mode
        if sym.choice and sym.visibility == 2:
            return "(*)" if sym.choice.selection is sym else "( )"

        tri_val_str = (" ", None, "*")[sym.tri_value]

        if len(sym.assignable) == 1:
            # Pinned to a single value
            return f"-{tri_val_str}-"

        if sym.type == BOOL:
            return f"[{tri_val_str}]"

        raise RuntimeError()

    @staticmethod
    def node_str(node, indent):
        """
        Returns the complete menu entry text for a menu node, or "" for
        invisible menu nodes. Invisible menu nodes are those that lack a prompt
        or that do not have a satisfied prompt condition.

        Example return value: "[*] Bool symbol (BOOL)"

        The symbol name is printed in parentheses to the right of the prompt.
        This is so that symbols can easily be referred to in the configuration
        interface.
        """
        if not node.prompt:
            return ""

        # Even for menu nodes for symbols and choices, it's wrong to check
        # Symbol.visibility / Choice.visibility here. The reason is that a
        # symbol (and a choice, in theory) can be defined in multiple
        # locations, giving it multiple menu nodes, which do not necessarily
        # all have the same prompt visibility. Symbol.visibility /
        # Choice.visibility is calculated as the OR of the visibility of all
        # the prompts.
        prompt, prompt_cond = node.prompt
        if not expr_value(prompt_cond):
            return ""

        if node.item == MENU:
            return f"    {indent * ' '}{prompt}  --->"

        if type(node.item) is Choice:
            return f"    {indent * ' '}{prompt}"

        if node.item == COMMENT:
            return f"    {indent * ' '}*** {prompt} ***"

        # Symbol
        sym = node.item

        if sym.type == UNKNOWN:
            return ""

        # {:3} sets the field width to three. Gives nice alignment for empty
        # string values.
        res = f"{Menuconfig.value_str(sym):3} {indent * ' '}{prompt}"

        # Append a sub-menu arrow if menuconfig and enabled
        if node.is_menuconfig:
            res += f"  ---{'>' if sym.tri_value > 0 else '-'}"

        return res

    @staticmethod
    def menu_node_strings(node, indent):
        items = []

        while node:
            string = Menuconfig.node_str(node, indent)
            if string:
                items.append((string, node))

            if (node.list and node.item != MENU
                    and (type(node.item) is Choice or not node.is_menuconfig)):
                items.extend(Menuconfig.menu_node_strings(node.list,
                                                          indent + 2))

            node = node.next

        return items

    def show_menu(self, title, top_node, is_submenu=False):
        selection = 0

        while True:
            items = Menuconfig.menu_node_strings(top_node, 0)

            height = len(items)
            scroll = 0
            if height > self.screen.height - 13:
                height = self.screen.height - 13
                scroll = 1

            buttons = [
                ('Build', 'build', 'B'),
                ('Save & Exit', 'save', 'S'),
                (' Exit ', 'exit', 'E'),
                (' Help ', 'help', 'h')
            ]
            if is_submenu:
                buttons.insert(0, (' Return ', 'return', 'ESC'))
            buttonbar = ButtonBar(self.screen, buttons)
            if not is_submenu:
                buttonbar.hotkeys['ESC'] = 'exit'
            listbox = Listbox(height, scroll=scroll, returnExit=1)
            count = 0
            for string, _ in items:
                listbox.append(string, count)
                if (selection == count):
                    listbox.setCurrent(count)
                count = count + 1

            grid = GridFormHelp(self.screen, title, None, 1, 2)
            grid.add(listbox, 0, 0, padding=(0, 0, 0, 1))
            grid.add(buttonbar, 0, 1, growx=1)
            grid.addHotKey(' ')

            rc = grid.runOnce()

            action = buttonbar.buttonPressed(rc)
            if action and action != 'help':
                return action

            if count == 0:
                continue

            selection = listbox.current()
            _, selected_node = items[selection]
            sym = selected_node.item

            if action == 'help':
                prompt, _ = selected_node.prompt
                if hasattr(selected_node, 'help') and selected_node.help:
                    help = selected_node.help
                else:
                    help = 'No help available.'
                ButtonChoiceWindow(
                    screen=self.screen,
                    title=f"Help on '{prompt}'",
                    text=help,
                    width=60,
                    buttons=['  Ok  '])
                continue

            show_submenu = False

            if type(sym) is Symbol:
                if rc == ' ':
                    if sym.type == BOOL:
                        sym.set_value('n' if sym.tri_value > 0 else 'y')
                else:
                    if selected_node.is_menuconfig:
                        show_submenu = True
                    elif sym.type in (STRING, INT, HEX):
                        action, values = EntryWindow(
                            screen=self.screen,
                            title=sym.name,
                            text=f'Enter a {TYPE_TO_STR[sym.type]} value:',
                            prompts=[('', sym.str_value)],
                            buttons=[('  Ok  ', 'Ok'), ('Cancel', '', 'ESC')])
                        if action == 'Ok':
                            self.kconf.warnings = []
                            val = values[0]
                            if sym.type == HEX and not val.startswith('0x'):
                                val = '0x' + val
                            sym.set_value(val)
                            # only fetching triggers range check - how ugly...
                            sym.str_value
                            if len(self.kconf.warnings) > 0:
                                ButtonChoiceWindow(
                                    screen=self.screen,
                                    title="Invalid entry",
                                    text="\n".join(self.kconf.warnings),
                                    width=60,
                                    buttons=['  Ok  '])
                                self.kconf.warnings = []
            elif selected_node.is_menuconfig and type(sym) is not Choice:
                show_submenu = True

            if show_submenu:
                submenu_title, _ = selected_node.prompt
                action = self.show_menu(submenu_title,
                                        selected_node.list,
                                        is_submenu=True)
                if action != 'return':
                    return action

    def show(self):
        self.screen = SnackScreen()

        action = self.show_menu(self.kconf.mainmenu_text,
                                self.kconf.top_node.list)

        self.screen.finish()
        return action


__KAS_PLUGINS__ = [Menu]
