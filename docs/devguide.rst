Developer Guide
===============

Deploy for development
----------------------

This project uses pip to manage the package. If you want to work on the
project yourself you can create the necessary links via::

    $ pip3 install --user -e .

That will install a backlink ~/.local/bin/kas to this project. Now you are
able to call it from anywhere.
For local development, use the **run-kas** wrapper from the project root
directory. In this case, replace ``kas`` with ``path/to/run-kas``.

Making Changes
--------------

These sections provide an overview of common modifications along with the
required steps.

Changes of the project configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When changing the project configuration, you need to update the json
configuration schema (``schema-kas.json``). Further, a short description of
the changes needs to be added to :doc:`format-changelog`.
After making the changes, you need to update the minimum and maximum values
of ``header.version``. If the version was already updated after the last
release, the version bump is not required.

Add a new CLI option
^^^^^^^^^^^^^^^^^^^^

Options that take a parameter (e.g. ``--format json``) must be handled
in ``kas-container`` as well. To keep the handling in ``kas-container``
simple, try to choose a unique option name across all plugins.

Add a new sub-command (plugin)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To add a new sub-command, you need to create a new python file in the
``kas/plugins`` directory. It then needs to be imported and registered
in ``kas/plugins/__init__.py``. Further, it needs to be registered in
``kas-container``, as well as in the ``container-entrypoint``.

Each sub-command must be documented and have its own man page. The
documentation is generated from the docstrings of the sub-command file and
must be registered in ``docs/userguide/plugins.rst``. In addition, a manpage
should be added in ``docs/_man/kas-plugin-<name>`` and registered in
``docs/conf.py`` (as ``kas-<name>.1``).

Add support for new credentials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Credentials are passed using environment variables. For details, see
:ref:`checkout-creds-label`. These can either contain the credential directly
or point to a credential file (e.g. ``.netrc``). To add support for a new
credential, the following steps are required:

- document the variable in :ref:`env-vars-label`
- add the variable to the ``ENV_VARS`` list in ``libcmds.py::SetupHome``
- add a forward of the variable in ``kas-container``
- add the variable to the ``test_environment_variables.py`` test

For variables pointing to a credential file, the following applies in addition:

- the variable should end in ``_FILE`` (exceptions may apply)
- ``kas-container``

  - bind-mount the variable into ``/var/kas/userdata/<credential file>``
  - rewrite the variable to the path inside the container

If the variable does not end in ``_FILE``, manual processing in the
``container-entrypoint`` script is needed to support it under rootless
docker.

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


Testing
-------

The kas project has an extensive test suite. When adding new features or fixing
bugs, it is recommended to add a test. The tests are written using the pytest
framework.

Decoupling from the calling environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please make sure to decouple the tests from your local environment.
To simplify this, we provide the ``monkeykas`` fixture to clean up the
environment prior to each test. When adding new kas environment variables,
make sure to add these to the cleanup handler as well.

When writing tests, no assumptions about the values of the following
environment variables should be made (they also can be unset):

- ``KAS_WORK_DIR``
- ``KAS_BUILD_DIR``

As tests might want to check data in the work or build dir, we provide the
following helpers to safely access the corresponding paths (by reading the
value from the environment variable at call time):

- ``monkeykas.get_kwd()``: absolute path to the current kas work dir
- ``monkeykas.get_kbd()``: absolute path to the current kas build dir
- ``monkeykas.move_to_kwd(path)``: move the path to into the ``KAS_WORK_DIR``,
  if needed

Tests that explicitly check for correct handling of the directory layout are
encouraged to parameterize these paths by temporarily setting them via
``monkeykas.setenv()``. Tests that rely on features that might be subject
to the current working directory should be marked with the ``dirsfromenv``
marker. By that, various combinations of ``KAS_WORK_DIR`` and ``KAS_BUILD_DIR``
are tested.

Executing the testsuite
^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    The menu plugin tests require the ``snack`` package to be installed. On
    most distros this is packaged in ``python3-newt``, on Arch Linux it is
    part of libnewt.

To run the tests, invoke::

    $ python3 -m pytest

Online and offline testing
^^^^^^^^^^^^^^^^^^^^^^^^^^

Some tests require internet access to fetch resources. These tests are marked
with the ``online`` marker. To run these tests, invoke::

    $ python3 -m pytest -m online

To run all tests except the online tests, invoke::

    $ python3 -m pytest -m "not online"

When adding new tests, please consider whether they require internet access or
not and mark them accordingly. In general, we prefer offline tests.

Measure code coverage
^^^^^^^^^^^^^^^^^^^^^

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
 - ``git@github.com:siemens/kas.git``

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
^^^^^^^^^^^^^^^^^^

.. automodule:: kas.kas
   :members:

``kas.libkas`` Module
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.libkas
   :members:

``kas.libcmds`` Module
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.libcmds
   :members:

``kas.config`` Module
^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.config
   :members:

``kas.repos`` Module
^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.repos
   :members:

``kas.includehandler`` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.includehandler
   :members:

``kas.kasusererror`` Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.kasusererror
   :members:

``kas.plugins`` Module
^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: kas.plugins
   :members:
