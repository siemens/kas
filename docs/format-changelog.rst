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