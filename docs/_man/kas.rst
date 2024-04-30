:orphan:

kas manpage
===========

.. argparse::
    :module: kas.kas
    :func: kas_get_argparser
    :prog: kas
    :manpage:

    .. include:: ../intro.rst
        :start-line: 3

PROJECT CONFIGURATION
---------------------

The project configuration file describes the build environment and the layers
to be used. It is the main input to kas.
For details, see :manpage:`kas-project-config(1)`

BUILD ATTESTATION
-----------------

Kas supports to generate build attestation. For details, see
:manpage:`kas-build-attestation(1)`.

CREDENTIAL HANDLING
-------------------

kas provides various mechanisms to inject credentials into the build.
For details, see :manpage:`kas-credentials(1)`.

ENVIRONMENT VARIABLES
---------------------

.. include:: ../command-line/environment-variables.inc

SEE ALSO
--------

:manpage:`kas-project-config(1)`,
:manpage:`kas-build(1)`,
:manpage:`kas-credentials(1)`

.. include:: _kas-man-footer.inc
