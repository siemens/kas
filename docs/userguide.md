User Guide
==========

Dependencies & installation
---------------------------

This projects depends on

- Python 3
- distro Python 3 package
- PyYAML Python 3 package (optional, for yaml file support)

If you need Python 2 support consider sending patches. The most
obvious place to start is to use the trollius package intead of
asyncio.

To install kas into your python site-package repository, run

```sh
$ sudo pip3 install .
```


Usage
-----

There are three options for using kas:
- Install it locally via pip to get the `kas` command.
- Use the docker image. In this case run the commands in the examples
below within `docker run -it <kas-image> sh` or bind-mount the project into the
container.
- Use the **run-kas** wrapper from this directory. In this case replace `kas`
in the examples below with `path/to/run-kas`.

Start build:

```sh
$ kas build /path/to/kas-project.yml
```

Alternatively, experienced bitbake users can invoke usual **bitbake** steps
manually, e.g.

```sh
$ kas shell /path/to/kas-project.yml -c 'bitbake dosfsutils-native'
```

kas will place downloads and build artifacts under the current directory when
being invoked. You can specify a different location via the environment variable
`KAS_WORK_DIR`.


Use Cases
---------

1.  Initial build/setup

    ```sh
    $ mkdir $PROJECT_DIR
    $ cd $PROJECT_DIR
    $ git clone $PROJECT_URL meta-project
    $ kas build meta-project/kas-project.yml
    ```

2.  Update/rebuild

    ```sh
    $ cd $PROJECT_DIR/meta-project
    $ git pull
    $ kas build kas-project.yml
    ```


Project Configuration
---------------------

Two types of input formats supported. For an product image
a the static configuration can be used. In case several different
configuration should be supported the dynamic configuration file can
be used.

##  Static project configuration

Currently there is supports for JSON and Yaml.

```YAML
header:
  version: "0.9"
machine: qemu
distro: poky
repos:
  # This entry includes the repository where the config file is located
  # to the bblayers.conf:
  meta-custom:
  # Here we include a list of layers from the poky repository to the
  # bblayers.conf:
  poky:
    url: "https://git.yoctoproject.org/git/poky"
    refspec: 89e6c98d92887913cadf06b2adb97f26cde4849b
    layers:
      meta:
      meta-poky:
      meta-yocto-bsp:
```

A minimal input file consist out of 'machine', 'distro', and 'repos'.

Additionally, you can add 'bblayers_conf_header' and 'local_conf_header'
which are strings that are added to the head of the respective files
(`bblayers.conf` or `local.conf`):

```YAML
bblayers_conf_header:
  meta-custom: |
    POKY_BBLAYERS_CONF_VERSION = "2"
    BBPATH = "${TOPDIR}"
    BBFILES ?= ""
local_conf_header:
  meta-custom: |
    PATCHRESOLVE = "noop"
    CONF_VERSION = "1"
    IMAGE_FSTYPES = "tar"
```

`meta-custom` in these examples should be a unique name (in project scope) for
this configuration entries. We assume that your configuration file is part of
a `meta-custom` repository/layer. This way its possible to overwrite or append
entries in files that include this configuration by naming an entry the same
(overwriting) or using a unused name (appending).

### Including in-tree configuration files

Its currently possible to include kas configuration files from the same
repository/layer like this:

```YAML
header:
  version: "0.9"
  includes:
    - base.yml
    - bsp.yml
    - product.yml
```

The specified files are addressed relative to your current configuration file.

### Including configuration files from other repos

Its also possible to include configuration files from other repos like this:

```YAML
header:
  version: "0.9"
  includes:
    - repo: poky
      file: kas-poky.yml
    - repo: meta-bsp-collection
      file: hw1/kas-hw-bsp1.yml
    - repo: meta-custom
      file: products/product.yml
repos:
  meta-custom:
  meta-bsp-collection:
    url: "https://www.example.com/git/meta-bsp-collection"
    refspec: 3f786850e387550fdab836ed7e6dc881de23001b
    layers:
      # Additional to the layers that are added from this repository
      # in the hw1/kas-hw-bsp1.yml, we add here an additional bsp
      # meta layer:
      meta-custom-bsp:
  poky:
    url: "https://git.yoctoproject.org/git/poky"
    refspec: 89e6c98d92887913cadf06b2adb97f26cde4849b
    layers:
      # If `kas-poky.yml` adds the `meta-yocto-bsp` layer and we
      # do not want it in our bblayers for this project, we can
      # overwrite it by setting:
      meta-yocto-bsp: exclude
```

The files are addressed relative to the git repository path.

The include mechanism collects and merges the content from top to buttom and
depth first. That means that settings in one include file are overwritten
by settings in a latter include file and entries from the last include file can
be overwritten by the current file. While merging all the dictionaries are
merged recursive while preserving the order in which the entries are added to
the dictionary. This means that `local_conf_header` entries are added to the
`local.conf` file in the same order in which they are defined in the different
include files. Note that the order of the configuration file entries is not
preserved within one include file, because the parser creates normal
unordered dictionaries.

##  Dynamic project configuration

The dynamic project configuration is plain Python with following
mandatory functions which need to be provided:

```Python
def get_machine(config):
    return 'qemu'


def get_distro(config):
    return 'poky'


def get_repos(target):
    repos = []

    repos.append(Repo(
        url='URL',
        refspec='REFSPEC'))

    repos.append(Repo(
        url='https://git.yoctoproject.org/git/poky',
        refspec='krogoth',
        layers=['meta', 'meta-poky', 'meta-yocto-bsp'])))

    return repos
```

Additionally, get_bblayers_conf_header(), get_local_conf_header() can
be added.

```Python
def get_bblayers_conf_header():
    return """POKY_BBLAYERS_CONF_VERSION = "2"
BBPATH = "${TOPDIR}"
BBFILES ?= ""
"""


def get_local_conf_header():
    return """PATCHRESOLVE = "noop"
CONF_VERSION = "1"
IMAGE_FSTYPES = "tar"
"""
```

Furthermore, you can add pre and post hooks (*_prepend, *_append) for
the exection steps in kas core, e.g.

```Python
def build_prepend(config):
    # disable distro check
    with open(config.build_dir + '/conf/sanity.conf', 'w') as f:
        f.write('\n')


def build_append(config):
    if 'CI' in os.environ:
        build_native_package(config)
        run_wic(config)
```

TODO: Document the complete configuration API.

## Environment variables

`KAS_REPO_RED_DIR` should point to a directory that contains
repositories that should be used as references. In order for kas to
find those repositories, they have to be named correctly. Those names
are derived from the repo url in the kas config.  (E.g. url:
"https://github.com/siemens/meta-iot2000.git" resolves to the name
"github.com.siemens.meta-iot2000.git")
