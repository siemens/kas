#
# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2024
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

ARG DEBIAN_TAG=bookworm-slim

FROM debian:${DEBIAN_TAG} AS kas-base

ARG SOURCE_DATE_EPOCH
ARG CACHE_SHARING=locked

ARG DEBIAN_TAG=bookworm-slim
ENV DEBIAN_BASE_IMAGE_TAG=${DEBIAN_TAG}

ARG TARGETPLATFORM
ARG DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.utf8
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING} \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-packages.conf && \
    if echo "${DEBIAN_TAG}" | grep -q "[0-9]"; then \
        sed -i -e '/^URIs:/d' -e 's|^# http://snapshot\.|URIs: http://snapshot.|' \
            /etc/apt/sources.list.d/debian.sources; \
        echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/use-snapshot.conf; \
        echo 'Acquire::Retries "10";' >> /etc/apt/apt.conf.d/use-snapshot.conf; \
        echo 'Acquire::Retries::Delay::Maximum "600";' >> /etc/apt/apt.conf.d/use-snapshot.conf; \
    fi && \
    apt-get update && \
    apt-get install -y locales && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    apt-get install --no-install-recommends -y \
        python3-pip python3-setuptools python3-wheel python3-yaml python3-distro python3-jsonschema \
        python3-newt python3-colorlog python3-kconfiglib python3-websockets \
        gosu lsb-release file vim less procps tree tar bzip2 zstd pigz lz4 unzip tmux libncurses-dev \
        git-lfs mercurial iproute2 ssh-client telnet curl rsync gnupg awscli sudo \
        socat bash-completion python3-shtab python3-git python3-gnupg python3-cairo && \
    rm -rf /var/log/* /tmp/* /var/tmp/* /var/cache/ldconfig/aux-cache && \
    rm -f /etc/gitconfig && \
    git config --system filter.lfs.clean 'git-lfs clean -- %f' && \
    git config --system filter.lfs.smudge 'git-lfs smudge -- %f' && \
    git config --system filter.lfs.process 'git-lfs filter-process' && \
    git config --system filter.lfs.required true

RUN --mount=type=bind,target=/kas,rw \
    pip3 --proxy=$https_proxy install \
        --no-deps \
        --no-build-isolation \
        --break-system-packages \
        /kas && \
    install -d /usr/local/share/bash-completion/completions/ && \
    shtab --shell=bash -u kas.kas.kas_get_argparser --error-unimportable --prog kas \
        > /usr/local/share/bash-completion/completions/kas && \
    rm -rf $(pip3 cache dir) && \
    rm -f /usr/local/bin/kas-container && \
    install -m 0755 /kas/contrib/oe-git-proxy /usr/bin/ && \
    install -m 0755 /kas/container-entrypoint / && \
    kas --version

ENV GIT_PROXY_COMMAND="oe-git-proxy" \
    NO_PROXY="*"

RUN echo "builder ALL=NOPASSWD: ALL" > /etc/sudoers.d/builder-nopasswd && \
    chmod 660 /etc/sudoers.d/builder-nopasswd && \
    echo "Defaults env_keep += \"ftp_proxy http_proxy https_proxy no_proxy\"" \
    > /etc/sudoers.d/env_keep && chmod 660 /etc/sudoers.d/env_keep && \
    groupadd builder -g 30000 && \
    useradd builder -u 30000 -g 30000 --create-home --home-dir /builder

ENTRYPOINT ["/container-entrypoint"]

#
# kas-isar image
#

FROM kas-base AS kas-isar

ARG SOURCE_DATE_EPOCH
ARG CACHE_SHARING=locked

# The install package list are actually taking 1:1 from their documentation,
# so there some packages that can already installed by other downstream layers.
# This will not change any image sizes on all the layers in use.
ENV LC_ALL=en_US.UTF-8
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING} \
    apt-get update && \
    apt-get install -y -f --no-install-recommends \
            binfmt-support bzip2 mmdebstrap arch-test apt-utils dosfstools \
            dpkg-dev gettext-base git mtools parted python3 python3-distutils \
            quilt qemu-user-static reprepro sudo unzip git-buildpackage \
            pristine-tar sbuild schroot zstd \
            umoci skopeo \
            python3-botocore \
            bubblewrap \
            debootstrap && \
    rm -rf /var/log/* /tmp/* /var/tmp/* /var/cache/ldconfig/aux-cache && \
    sbuild-adduser builder && \
    sed -i 's|# kas-isar: ||g' /container-entrypoint

USER builder

#
# kas image
#

FROM kas-base AS kas

ARG SOURCE_DATE_EPOCH
ARG CACHE_SHARING=locked

# The install package list are actually taking 1:1 from their documentation
# (exception: pylint3 -> pylint),  so there some packages that can already
# installed by other downstream layers. This will not change any image sizes
# on all the layers in use.
RUN --mount=type=cache,target=/var/cache/apt,sharing=${CACHE_SHARING} \
    --mount=type=cache,target=/var/lib/apt,sharing=${CACHE_SHARING} \
    apt-get update && \
    apt-get install --no-install-recommends -y \
        gawk wget git diffstat unzip texinfo \
        gcc build-essential chrpath socat cpio python3 python3-pip python3-pexpect \
        xz-utils debianutils iputils-ping python3-git python3-jinja2 libegl1-mesa libsdl1.2-dev \
        pylint xterm python3-subunit mesa-common-dev zstd liblz4-tool && \
    if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
        apt-get install --no-install-recommends -y gcc-multilib g++-multilib; \
    fi && \
    rm -rf /var/log/* /tmp/* /var/tmp/* /var/cache/ldconfig/aux-cache

USER builder
