#!/usr/bin/env python3
# takes a reverse-sorted, line separated list and
# returns the first element that is equal or smaller
# than the first argument

import sys

for line in sys.stdin:
    if line.rstrip() <= sys.argv[1]:
        print(line.rstrip())
        break
