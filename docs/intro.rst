Introduction and installation
=============================

This tool provides an easy mechanism to setup bitbake based
projects.

The OpenEmbedded tooling support starts at step 2 with bitbake. The
downloading of sources and then configuration has to be done by
hand. Usually, this is explained in a README. Instead kas is using a
project configuration file and does the download and configuration
phase.

Currently supported Yocto versions:

- 2.1 (Krogoth)
- 2.2 (Morty)

Older or newer versions may work as well but haven't been tested intensively.

Key features provided by the build tool:

- clone and checkout bitbake layers
- create default bitbake settings (machine, arch, ...)
- launch minimal build environment, reducing risk of host contamination
- initiate bitbake build process
