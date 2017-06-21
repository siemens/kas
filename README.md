Setup tool for bitbake based projects
=====================================

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


Dependencies & installation
---------------------------

This projects depends on

- Python 3
- distro Python 3 package
- PyYAML Python 3 package

If you need Python 2 support consider sending patches. The most
obvious place to start is to use the trollius package intead of
asyncio.

To install kas into your python site-package repository, run

```sh
$ sudo pip install
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

```JSON
{
    "machine": "qemu",
    "distro": "poky",
    "repos": [
        { "url": "" },
        { "url": "https://git.yoctoproject.org/git/poky",
          "refspec": "krogoth",
          "sublayers": [ "meta", "meta-poky", "meta-yocto-bsp"]}
    ]
}
```

A minimal input file consist out of 'machine', 'distro', and 'repos'.

Additionally, you can add 'bblayers_conf_header' and 'local_conf_header'
which are arrays of strings, e.g.

```JSON
    "bblayers_conf_header": ["POKY_BBLAYERS_CONF_VERSION = \"2\"",
                             "BBPATH = \"${TOPDIR}\"",
                             "BBFILES ?= \"\""],
    "local_conf_header": ["PATCHRESOLVE = \"noop\"",
                          "CONF_VERSION = \"1\"",
                          "IMAGE_FSTYPES = \"tar\""]
```

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
        sublayers=['meta', 'meta-poky', 'meta-yocto-bsp'])))

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


Development
-----------

This project uses pip to manage the package. If you want to work on the
project yourself you can create the necessary links via:

```sh
$ sudo pip install -e .
```

That will install a backlink /usr/bin/kas to this project. Now you are
able to call it from anywhere.


Docker image build
------------------

Just run

```sh
$ docker build -t <image_name> .
```

When you need a proxy to access the internet, add `--build-arg
http_proxy=<http_proxy> --build-arg https_proxy=<https_proxy>` to the
call.


Community Resources
-------------------

Project home:

 - https://github.com/siemens/kas

Source code:

 - https://github.com/siemens/kas.git
 - git@github.com:siemens/kas.git

Mailing list:

  - kas-devel@googlegroups.com

  - Subscription:
    - kas-devel+subscribe@googlegroups.com
    - https://groups.google.com/forum/#!forum/kas-devel/join

  - Archives
    - https://groups.google.com/forum/#!forum/kas-devel
    - https://www.mail-archive.com/kas-devel@googlegroups.com/
