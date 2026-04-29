# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2026
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

import pytest
from kas.attestation import Provenance


@pytest.mark.parametrize('url,expected', [
    # plain https
    ('https://example.com/siemens/kas.git',
     'https://example.com/siemens/kas.git'),
    # https with user:password
    ('https://user:password@example.com/siemens/kas.git',
     'https://example.com/siemens/kas.git'),
    # https with user only
    ('https://user@example.com/siemens/kas.git',
     'https://example.com/siemens/kas.git'),
    # https with port and credentials
    ('https://user:password@example.com:8443/siemens/kas.git',
     'https://example.com:8443/siemens/kas.git'),
    # http with credentials
    ('http://token:x-oauth-basic@example.com/repo.git',
     'http://example.com/repo.git'),
    # ssh without credentials
    ('ssh://git@example.com/siemens/kas.git',
     'ssh://example.com/siemens/kas.git'),
    # plain URL without credentials
    ('https://example.com/path?query=1#frag',
     'https://example.com/path?query=1#frag'),
    # empty string
    ('', ''),
])
def test_strip_credentials(url, expected):
    assert Provenance._strip_credentials(url) == expected
