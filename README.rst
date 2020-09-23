Setup tool for bitbake based projects
=====================================

+--------------------+
|    Build Status    |
+====================+
| |workflow-master|_ |
+--------------------+
| |workflow-next|_   |
+--------------------+

.. |workflow-master| image:: https://github.com/siemens/kas/workflows/master/badge.svg
.. _workflow-master: https://github.com/siemens/kas/actions?query=workflow%3Amaster
.. |workflow-next| image:: https://github.com/siemens/kas/workflows/next/badge.svg
.. _workflow-next: https://github.com/siemens/kas/actions?query=workflow%3Anext

This tool provides an easy mechanism to setup bitbake based
projects.

The OpenEmbedded tooling support starts at step 2 with bitbake. The
downloading of sources and then configuration has to be done by
hand. Usually, this is explained in a README. Instead kas is using a
project configuration file and does the download and configuration
phase.

Key features provided by the build tool:

- clone and checkout bitbake layers
- create default bitbake settings (machine, arch, ...)
- launch minimal build environment, reducing risk of host contamination
- initiate bitbake build process

See the `kas documentation <https://kas.readthedocs.io>`_ for further details.
