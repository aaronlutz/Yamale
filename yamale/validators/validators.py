import re
from datetime import date, datetime
from .base import Validator
from . import constraints as con
from .. import util

# ABCs for containers were moved to their own module
try:
    from collections.abc import Sequence, Mapping
except ImportError:
    from collections import Sequence, Mapping


class String(Validator):
    """String validator"""
    tag = 'str'
    constraints = [con.LengthMin, con.LengthMax, con.CharacterExclude, con.StringValue]

    def _is_valid(self, value):
        return util.isstr(value)


class Number(Validator):
    """Number/float validator"""
    value_type = float
    tag = 'num'
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, (int, float))


class Integer(Validator):
    """Integer validator"""
    value_type = int
    tag = 'int'
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, int)


class Boolean(Validator):
    """Boolean validator"""
    tag = 'bool'
    constraints = [con.BooleanValue]

    def _is_valid(self, value):
        return isinstance(value, bool)


class Enum(Validator):
    """Enum validator"""
    tag = 'enum'

    def __init__(self, *args, **kwargs):
        super(Enum, self).__init__(*args, **kwargs)
        self.enums = args

    def _is_valid(self, value):
        return value in self.enums

    def fail(self, value):
        return '\'%s\' not in %s' % (value, self.enums)


class Day(Validator):
    """Day validator. Format: YYYY-MM-DD"""
    value_type = date
    tag = 'day'
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, date)


class Timestamp(Validator):
    """Timestamp validator. Format: YYYY-MM-DD HH:MM:SS"""
    value_type = datetime
    tag = 'timestamp'
    constraints = [con.Min, con.Max]

    def _is_valid(self, value):
        return isinstance(value, datetime)


class Map(Validator):
    """Map and dict validator"""
    tag = 'map'

    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        self.validators = [val for val in args if isinstance(val, Validator)]

    def _is_valid(self, value):
        return isinstance(value, Mapping)


class RedshiftDatatype(Validator):
    tag = 'redshift_datatype'
    constraints = [con.SpecificDatatype]

    single_arg_pattern = "^[a-zA-Z\s]+\((\d+|MAX)\)"
    multiple_arg_pattern = "^[a-zA-Z\s]+\((\d+[,]{1}[ ]?\d+|MAX)\)"

    aliases = {'CHAR': 'CHAR', 'CHARACTER': 'CHAR', 'BPCHAR': 'CHAR', 'NCHAR': 'CHAR', 'VARCHAR': 'VARCHAR',
               'CHARACTER VARYING': 'VARCHAR', 'NVARCHAR': 'VARCHAR'}
    str_ranges = {'CHAR': (1, 4096), 'VARCHAR': (1, 65535)}
    num_ranges = {'PRECISION': (1, 38), 'SCALE': (0, 37)}

    one_optional_arg = ['CHAR', 'CHARACTER', 'NCHAR', 'BPCHAR', 'VARCHAR', 'CHARACTER VARYING', 'NVARCHAR']
    two_optional_args = ['DECIMAL', 'NUMERIC']
    no_optional_args = ['SMALLINT', 'INT2', 'INTEGER', 'INT', 'INT4', 'BIGINT', 'INT8', 'REAL', 'FLOAT4', 'DATE',
                        'DOUBLE PRECISION', 'FLOAT8', 'FLOAT', 'BOOLEAN', 'BOOL', 'TIMESTAMP', 'TIMESTAMPTZ',
                        'TIMESTAMP WITHOUT TIME ZONE', 'TIMESTAMP WITH TIME ZONE', 'GEOMETRY', 'TEXT']

    all_args = one_optional_arg + two_optional_args + no_optional_args

    def __init__(self, *args, **kwargs):
        super(RedshiftDatatype, self).__init__(*args, **kwargs)
        self.validators = [val for val in args if isinstance(val, Validator)]

    def _is_valid(self, value):

        def valid_without_argument():
            return value.upper() in self.all_args

        def valid_single_argument():
            valid = False
            if re.findall(self.single_arg_pattern, value):
                type_ = value.split('(')[0]
                arg_ = re.search(r'\((.*?)\)', value).group(1).replace(" ", "")

                if type_ in self.one_optional_arg:
                    valid_range = self.str_ranges[self.aliases[type_]]
                    valid = arg_ == 'MAX' or valid_range[0] <= int(arg_) <= valid_range[1]

            return valid

        def valid_double_argument():
            if re.findall(self.multiple_arg_pattern, value):
                type_ = value.split('(')[0]
                if type_ in self.two_optional_args:
                    args_ = [int(x) for x in re.search(r'\((.*?)\)', value).group(1).replace(" ", "").split(",")]
                    valid_precision = self.num_ranges['PRECISION'][0] <= args_[0] <= self.num_ranges['PRECISION'][1]
                    valid_scale = self.num_ranges['SCALE'][0] <= args_[1] <= self.num_ranges['SCALE'][1]
                    if valid_precision and valid_scale and args_[0] > args_[1]:
                        return True

        if not isinstance(value, str):
            return False

        return any([valid_without_argument(), valid_single_argument(), valid_double_argument()])


class List(Validator):
    """List validator"""
    tag = 'list'
    constraints = [con.LengthMin, con.LengthMax]

    def __init__(self, *args, **kwargs):
        super(List, self).__init__(*args, **kwargs)
        self.validators = [val for val in args if isinstance(val, Validator)]

    def _is_valid(self, value):
        return isinstance(value, Sequence) and not util.isstr(value)


class Include(Validator):
    """Include validator"""
    tag = 'include'

    def __init__(self, *args, **kwargs):
        self.include_name = args[0]
        self.strict = kwargs.pop('strict', None)
        super(Include, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return True

    def get_name(self):
        return self.include_name


class Any(Validator):
    """Any of several types validator"""
    tag = 'any'

    def __init__(self, *args, **kwargs):
        self.validators = [val for val in args if isinstance(val, Validator)]
        super(Any, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return True


class Null(Validator):
    """Validates null"""
    value_type = None
    tag = 'null'

    def _is_valid(self, value):
        return value is None


class Regex(Validator):
    """Regular expression validator"""
    tag = 'regex'
    _regex_flags = {'ignore_case': re.I, 'multiline': re.M, 'dotall': re.S}

    def __init__(self, *args, **kwargs):
        self.regex_name = kwargs.pop('name', None)

        flags = 0
        for k, v in util.get_iter(self._regex_flags):
            flags |= v if kwargs.pop(k, False) else 0

        self.regexes = [re.compile(arg, flags) for arg in args if util.isstr(arg)]
        super(Regex, self).__init__(*args, **kwargs)

    def _is_valid(self, value):
        return util.isstr(value) and any(r.match(value) for r in self.regexes)

    def get_name(self):
        return self.regex_name or self.tag + " match"


class Ip(Validator):
    """IP address validator"""
    tag = 'ip'
    constraints = [con.IpVersion]

    def _is_valid(self, value):
        return self.ip_address(value)

    def ip_address(self, value):
        try:
            import ipaddress
        except ImportError:
            raise ImportError("You must install the ipaddress backport in Py2")
        try:
            ipaddress.ip_interface(util.to_unicode(value))
        except ValueError:
            return False
        return True

class Mac(Regex):
    """MAC address validator"""
    tag = 'mac'

    def __init__(self, *args, **kwargs):
        super(Mac, self).__init__(*args, **kwargs)
        self.regexes = [
            re.compile("[0-9a-fA-F]{2}([-:]?)[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$"),
            re.compile("[0-9a-fA-F]{4}([-:]?)[0-9a-fA-F]{4}(\\1[0-9a-fA-F]{4})$"),
        ]


DefaultValidators = {}

for v in util.get_subclasses(Validator):
    # Allow validator nodes to contain either tags or actual name
    DefaultValidators[v.tag] = v
    DefaultValidators[v.__name__] = v
