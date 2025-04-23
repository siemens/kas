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

"""
    This module provides a common base class for all exceptions
    which are related to user or configuration errors. These exceptions
    should be caught and reported to the user using a meaningful message
    instead of a stacktrace.

    When handling errors in KAS, never return directly using `sys.exit`,
    but instead throw an exception derived from :class:`KasUserError` (for user
    errors), or one derived from `Exception` for internal errors. These
    are then handled centrally, mapped to correct return codes and pretty
    printed.
"""


__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2023'


class KasUserError(Exception):
    """
    User or input error. Derive all user error exceptions from this class.
    """
    pass


class CommandExecError(KasUserError):
    """
    Failure in execution of a shell command. The `forward_error_code` parameter
    can be used to request the receiver of the exception to `sys.exit` with
    that code instead of a generic one. Only use this in special cases, where
    the return code can actually be related to a single shell command.
    """
    def __init__(self, command, ret_code,
                 forward_ret_code=False):
        self.ret_code = ret_code
        self.forward = forward_ret_code
        message = ' '.join([f"'{c}'" if ' ' in c else c for c in command])
        super().__init__(f'Command "{message}" failed with error {ret_code}')


class ArgsCombinationError(KasUserError):
    """
    Invalid combination of CLI arguments provided
    """
    def __init__(self, message):
        super().__init__(f'Invalid combination of arguments: {message}')


class ArtifactNotFoundError(KasUserError, FileNotFoundError):
    """
    A configured artifact is not found (or the glob matches 0 elements).
    """
    def __init__(self, name, artifact):
        super().__init__(f'No artifact found for {name}:"{artifact}"')


class EnvSetButNotFoundError(KasUserError, FileNotFoundError):
    """
    A environment variable pointing to a file or directory is set, but
    the path it points to does not exist.
    """
    def __init__(self, env_name, path):
        super().__init__(f'Environment variable "{env_name}" is set, but the '
                         f'path does not exist: {path}')


class MissingModuleError(KasUserError):
    """
    An optional module is missing for the requested operation
    """
    def __init__(self, module, operation) -> None:
        super().__init__(f'Module "{module}" is required for: {operation}')
