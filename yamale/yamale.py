#!/usr/bin/env python
import sys
import os
from .schema import Schema

PY2 = sys.version_info[0] == 2


def make_schema(path, parser='PyYAML', validators=None, raw_schema_=None):
    # validators = None means use default.
    # Import readers here so we can get version information in setup.py.
    from . import readers
    raw_schemas = [raw_schema_] if raw_schema_ else readers.parse_file(path, parser)
    if not raw_schemas:
        raise ValueError('{} is an empty file!'.format(path))
    # First document is the base schema
    try:
        s = Schema(raw_schemas[0], path, validators=validators)
        # Additional documents contain Includes.
        for raw_schema in raw_schemas[1:]:
            s.add_include(raw_schema)
    except (TypeError, SyntaxError) as e:
        error = 'Schema error in file %s\n' % path
        error += str(e)
        if PY2:
            error.encode('utf-8')
        raise SyntaxError(error)

    return s


def make_data(path, parser='PyYAML', raw_data_=None):
    from . import readers
    raw_data = [raw_data_] if raw_data_ else readers.parse_file(path, parser)
    if len(raw_data) == 0:
        return [({}, path)]
    return [(d, path) for d in raw_data]


def validate(schema, data, strict=False):
    for d, path in data:
        schema.validate(d, path, strict)
    return data
