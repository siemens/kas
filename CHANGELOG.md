0.12.0
- Remove dynamic configuration support (Python config files)
- Shell command prepares complete bitbake configuration
- Add to define task in config and environment
- Improved error handling and reporting

0.11.0
- Allow in-tree repos not to be in a git repo
- Pass through git proxy related environment variables
- Write deterministic local.conf and bblayers.con
- Make configuration file versioning independent of project version
- Cleanups for uploading project to PyPI
- Print proper error message for config file format exception

0.10.0
- Docker image creation (Debian Stretch), pushed on kasproject/kas
- Restructure documentation add support for Sphinx export it to readthedocs
- Add support for include feature for Yaml files
- Add support for Isar build system
- Handling of SIGTERM/TERM improved
- Parallel download of git sources
- Allow environment to overwrite proxy, target, machine and distro
- Add unit testing for include/merge config file handling
- Rename sublayers back to layers
- pylint & pep8 cleanups
- Allow to define workdir via KAS_WORK_DIR
- Shell honors SHELL and TERM environment variable

0.9.0
- initial public release
