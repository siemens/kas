# This image builds Yocto 2.2 jobs using the kas tool

FROM ubuntu:16.04

ENV LOCALE=en_US.UTF-8
RUN apt-get update && apt-get install -y locales && \
    sed -i -e "s/# $LOCALE.*/$LOCALE UTF-8/" /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

RUN apt-get -y install gawk wget git-core diffstat unzip \
                       texinfo gcc-multilib build-essential \
		       chrpath socat cpio python python3 \
		       libsdl1.2-dev xterm tar bzip2 curl \
		       dosfstools mtools parted syslinux tree \
		       python3-pip bc gosu python3-yaml
COPY . /kas
RUN pip3 install /kas

COPY docker-entrypoint /docker-entrypoint
ENTRYPOINT ["/docker-entrypoint"]
