# kas - setup tool for bitbake based projects
#
# Copyright (c) Siemens AG, 2017-2018
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
    This module contains the schema of the configuration file.
'''
__license__ = 'MIT'
__copyright__ = 'Copyright (c) Siemens AG, 2017-2018'

CONFIGSCHEMA = {
    'type': 'object',
    'required': ['header'],
    'additionalProperties': False,
    'properties': {
        'header': {
            'type': 'object',
            'required': ['version'],
            'additionalProperties': False,
            'properties': {
                'version': {
                    'oneOf': [
                        {
                            'type': 'string',
                            'enum': ['0.10'],
                        },
                        {
                            'type': 'integer',
                        },
                    ],
                },
                'includes': {
                    'type': 'array',
                    'items': {
                        'oneOf': [
                            {
                                'type': 'string',
                            },
                            {
                                'type': 'object',
                                'required': ['repo', 'file'],
                                'additionalProperties': False,
                                'properties': {
                                    'repo': {
                                        'type': 'string',
                                    },
                                    'file': {
                                        'type': 'string'
                                    },
                                },
                            },
                        ],
                    },
                },
            },
        },
        'defaults': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'repos': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'refspec': {
                            'type': 'string',
                        },
                        'patches': {
                            'type': 'object',
                            'additionalProperties': False,
                            'properties': {
                                'repo': {
                                    'type': 'string',
                                },
                            },
                        },
                    },
                },
            },
        },
        'machine': {
            'type': 'string',
        },
        'distro': {
            'type': 'string',
        },
        'env': {
            'type': 'object',
            'additionalProperties': {
                'type': 'string',
            },
        },
        'target': {
            'oneOf': [
                {
                    'type': 'string',
                },
                {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                    },
                },
            ],
        },
        'task': {
            'type': 'string',
        },
        'repos': {
            'type': 'object',
            'additionalProperties': {
                'oneOf': [
                    {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'name': {
                                'type': 'string',
                            },
                            'url': {
                                'type': 'string',
                            },
                            'type': {
                                'type': 'string',
                            },
                            'refspec': {
                                'type': 'string',
                            },
                            'path': {
                                'type': 'string',
                            },
                            'layers': {
                                'type': 'object',
                                'additionalProperties': {
                                    'oneOf': [
                                        {
                                            'type': 'null',
                                        },
                                        {
                                            'type': 'integer',
                                        },
                                        {
                                            'type': 'boolean',
                                        },
                                        {
                                            'type': 'string',
                                        },
                                    ],
                                },
                            },
                            'patches': {
                                'type': 'object',
                                'additionalProperties': {
                                    'oneOf': [
                                        {
                                            'type': 'object',
                                            'additionalProperties': False,
                                            'required': ['path'],
                                            'properties': {
                                                'repo': {
                                                    'type': 'string'
                                                },
                                                'path': {
                                                    'type': 'string'
                                                },
                                            },
                                        },
                                        {
                                            'type': 'null'
                                        },
                                    ],
                                },
                            },
                        },
                    },
                    {
                        'type': 'null',
                    },
                ],
            },
        },
        'bblayers_conf_header': {
            'type': 'object',
            'additionalProperties': {
                'type': 'string',
            },
        },
        'local_conf_header': {
            'type': 'object',
            'additionalProperties': {
                'type': 'string',
            },
        },
        'proxy_config': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {
                'http_proxy': {
                    'type': 'string',
                },
                'https_proxy': {
                    'type': 'string',
                },
                'ftp_proxy': {
                    'type': 'string',
                },
                'no_proxy': {
                    'type': 'string',
                },
            },
        },
    },
}
