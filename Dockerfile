#
# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2023
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

FROM debian:bookworm-slim as kas-base

ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.utf8
RUN apt-get update && \
    apt-get install -y locales && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    apt-get install --no-install-recommends -y \
        python3-pip python3-setuptools python3-wheel python3-yaml python3-distro python3-jsonschema \
        python3-newt python3-colorlog python3-kconfiglib \
        gosu lsb-release file vim less procps tree tar bzip2 zstd pigz lz4 unzip tmux libncurses-dev \
        git-lfs mercurial iproute2 ssh-client telnet curl rsync gnupg awscli sudo \
        socat bash-completion && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY . /kas
RUN chmod -R o-w /kas

RUN pip3 --proxy=$https_proxy install \
        --no-deps \
        --no-build-isolation \
        --break-system-packages \
        /kas && \
    kas --version && \
    rm -rf $(pip3 cache dir)

RUN ln -s /kas/contrib/oe-git-proxy /usr/bin/
ENV GIT_PROXY_COMMAND="oe-git-proxy" \
    NO_PROXY="*"

RUN echo "builder ALL=NOPASSWD: ALL" > /etc/sudoers.d/builder-nopasswd && \
    chmod 660 /etc/sudoers.d/builder-nopasswd

RUN echo "Defaults env_keep += \"ftp_proxy http_proxy https_proxy no_proxy\"" \
    > /etc/sudoers.d/env_keep && chmod 660 /etc/sudoers.d/env_keep

RUN groupadd builder -g 30000 && \
    useradd builder -u 30000 -g 30000 --create-home --home-dir /builder

ENTRYPOINT ["/kas/container-entrypoint"]

#
# kas-isar image
#

FROM kas-base as kas-isar

# The install package list are actually taking 1:1 from their documentation,
# so there some packages that can already installed by other downstream layers.
# This will not change any image sizes on all the layers in use.
ENV LC_ALL=en_US.UTF-8
RUN apt-get update && \
    apt-get install -y -f --no-install-recommends \
            binfmt-support bzip2 mmdebstrap arch-test apt-utils dosfstools \
            dpkg-dev gettext-base git mtools parted python3 python3-distutils \
            quilt qemu-user-static reprepro sudo unzip git-buildpackage \
            pristine-tar sbuild schroot zstd \
            umoci skopeo \
            debootstrap && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    sbuild-adduser builder && \
    sed -i 's|# kas-isar: ||g' /kas/container-entrypoint

USER builder

#
# kas image
#

FROM kas-base as kas

# The install package list are actually taking 1:1 from their documentation
# (exception: pylint3 -> pylint),  so there some packages that can already
# installed by other downstream layers. This will not change any image sizes
# on all the layers in use.
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        gawk wget git diffstat unzip texinfo \
        gcc build-essential chrpath socat cpio python3 python3-pip python3-pexpect \
        xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev \
        pylint xterm python3-subunit mesa-common-dev zstd liblz4-tool && \
    if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        apt-get install --no-install-recommends -y gcc-multilib g++-multilib; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

USER builder
