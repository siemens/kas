#!/bin/sh
#
# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2024
#
# Authors:
#  Felix Moessbauer <felix.moessbauer@siemens.com>
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

# Extract the usage information of kas-container and convert it to rst
# to be included in the documentation.

cat - | \
    sed    's/^Usage:/|SYNOPSIS|\n----------\n/g' | \
    sed -e 's/^\s*kas-container /| kas-container /g' | \
    # unwrap long lines
    perl -0pe 's/\n\s\s+/ /g' | \
    sed    's/^Positional arguments:/|KAS-COMMANDS|\n--------------/g' | \
    # each commands starts with a new line
    sed -r 's/^(build|checkout|diff|dump|lock|shell|for-all-repos|clean|cleansstate|cleanall|purge|menu)\t\t*(.*)$/:\1: \2/g' | \
    sed    's/^Optional arguments:/|OPTIONS|\n---------/g' | \
    sed    '/^You can force/d' | \
    cat
