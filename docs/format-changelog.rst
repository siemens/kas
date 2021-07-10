Configuration Format Changes
============================

Version 1 (Alias '0.10')
------------------------

Added
~~~~~

- Include mechanism
- Version check


Version 2
---------

Changed
~~~~~~~

- Configuration file versions are now integers

Fixed
~~~~~

- Including files from repos that are not defined in the current file

Version 3
---------

Added
~~~~~

- ``Task`` key that allows to specify which task to run (``bitbake -c``)

Version 4
---------

Added
~~~~~

- ``Target`` key now allows to be a list of target names

Version 5
---------

Changed behavior
~~~~~~~~~~~~~~~~

- Using ``multiconfig:*`` targets adds appropriate ``BBMULTICONFIG`` entries to
  the ``local.conf`` automatically.

Version 6
---------

Added
~~~~~

- ``env`` key now allows to pass custom environment variables to the bitbake
  build process.

Version 7
---------

Added
~~~~~

- ``type`` property to ``repos`` to be able to express which version control
  system to use.

Version 8
---------

Added
~~~~~

- ``patches`` property to ``repos`` to be able to apply additional patches to
  the repo.

Version 9
---------

Added
~~~~~

- ``defaults`` key can now be used to set a default value for the repository
  property ``refspec`` and the repository patch property ``repo``. These
  default values will be used if the appropriate properties are not defined
  for a given repository or patch.

Version 10
----------

Added
~~~~~

- ``build_system`` property to pre-select OE or Isar.

Version 11
----------

Added
~~~~~

- ``menu_configuration`` key stores the selections done via ``kas menu`` in a
  configuration file. It is only evaluated by that plugin.
