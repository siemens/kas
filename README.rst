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

SECURITY NOTICE
---------------

kas relies on the respective version control system to ensure the integrity of
fetched repositories. Most upstream repositories are using git or hg with SHA-1
which may be subject to hash collision attacks. Therefore, make sure to only
pull from trusted sources to ensure that the selected revisions are the
expected ones, specifically when using mirrors. Later versions of kas may
introduce integrity validation mechanisms such as cryptographic checksums to
strengthen supply chain security.
