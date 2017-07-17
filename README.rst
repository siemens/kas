Setup tool for bitbake based projects
=====================================

+------------+------------------+
|   Branch   |   Build Status   |
+============+==================+
| ``master`` | |travis-master|_ |
+------------+------------------+
| ``next``   | |travis-next|_   |
+------------+------------------+

.. |travis-master| image:: https://travis-ci.org/siemens/kas.svg?branch=master
.. _travis-master: https://travis-ci.org/siemens/kas/branches
.. |travis-next| image:: https://travis-ci.org/siemens/kas.svg?branch=next
.. _travis-next: https://travis-ci.org/siemens/kas/branches

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
