Developer Guide
===============

Deploy for development
----------------------

This project uses pip to manage the package. If you want to work on the
project yourself you can create the necessary links via::

    $ pip3 install --user -e .

That will install a backlink ~/.local/bin/kas to this project. Now you are
able to call it from anywhere.


Container image build
---------------------

To build the container images kas provides, there is a script provided for
your convenience. It uses docker buildx and requires BuildKit 0.13.0 or newer.
To start the build both container variants, invoke::

    $ scripts/build-container.sh

You can limit the target type to either Yocto/OE (``kas``) or isar
(``kas-isar``) via the ``--target`` options. See the script help for more
options.

Since release 4.3, the containers officially provided via ghcr.io are fully
reproducible. To test this, you can use the following script, e.g. to validate
that release::

    $ scripts/reproduce-container.sh kas:4.3

Both scripts also support building/checking of the arm64 container images. See
the help of both scripts for more details.


Measure code coverage
---------------------

To measure the code coverage of the unit tests, the ``pytest-cov`` package is
required. On Debian systems, this is provided in ``python3-pytest-cov``.
Once installed, run::

    $ python3 -m pytest --cov --cov-report html

The coverage in HTML format can then be found in `htmlcov`.


Community Resources
-------------------

Project home:

 - https://github.com/siemens/kas

Source code:

 - https://github.com/siemens/kas.git
 - git@github.com:siemens/kas.git

Documentation:

 - https://kas.readthedocs.org

Mailing list:

  - kas-devel@googlegroups.com

  - Subscription:

    - kas-devel+subscribe@googlegroups.com
    - https://groups.google.com/forum/#!forum/kas-devel/join

  - Archives

    - https://groups.google.com/forum/#!forum/kas-devel
    - https://www.mail-archive.com/kas-devel@googlegroups.com/

Class reference documentation
-----------------------------

``kas.kas`` Module
..................

.. automodule:: kas.kas
   :members:

``kas.libkas`` Module
.....................

.. automodule:: kas.libkas
   :members:

``kas.libcmds`` Module
......................

.. automodule:: kas.libcmds
   :members:

``kas.config`` Module
.....................

.. automodule:: kas.config
   :members:

``kas.repos`` Module
....................

.. automodule:: kas.repos
   :members:

``kas.includehandler`` Module
.............................

.. automodule:: kas.includehandler
   :members:

``kas.kasusererror`` Module
.............................

.. automodule:: kas.kasusererror
   :members:

``kas.plugins`` Module
......................

.. automodule:: kas.plugins
   :members:
