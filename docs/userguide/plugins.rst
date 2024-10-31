Sub-commands (Plugins)
======================

kas sub-commands are implemented by a series of plugins. Each plugin
typically provides a single command.

``build`` plugin
----------------

.. automodule:: kas.plugins.build

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: build

``checkout`` plugin
-------------------

.. automodule:: kas.plugins.checkout

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: checkout


``dump`` plugin
---------------

.. automodule:: kas.plugins.dump

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: dump

``for-all-repos`` plugin
------------------------

.. automodule:: kas.plugins.for_all_repos

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: for-all-repos

``lock`` plugin
------------------------

.. automodule:: kas.plugins.lock

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: lock

``menu`` plugin
---------------

.. automodule:: kas.plugins.menu

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: menu

``shell`` plugin
----------------

.. automodule:: kas.plugins.shell

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: shell
