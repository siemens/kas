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

``clean`` plugin
----------------

.. automodule:: kas.plugins.clean

``clean`` command
^^^^^^^^^^^^^^^^^

.. automodule:: kas.plugins.clean.Clean

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: clean

``cleansstate`` command
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.plugins.clean.CleanSstate

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: cleansstate

``cleanall`` command
^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.plugins.clean.CleanAll

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: cleanall

``diff`` plugin
----------------

.. automodule:: kas.plugins.diff

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: diff

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

``purge`` plugin
----------------

.. automodule:: kas.plugins.clean.Purge

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: purge

``shell`` plugin
----------------

.. automodule:: kas.plugins.shell

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :path: shell
