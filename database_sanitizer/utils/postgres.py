# -*- coding: utf-8 -*-
"""
Contains utilities for working with Postgres `COPY` command, mainly encoding
and decoding values in the custom format used by Postgres.

Documentation about copy command and the text format used by it can be found
from:
https://www.postgresql.org/docs/9.2/static/sql-copy.html
"""

from __future__ import unicode_literals

import re
import string

import six

#: Representation of NULL value in Postgres COPY statement.
POSTGRES_COPY_NULL_VALUE = "\\N"


DECODE_REGEX = re.compile(r'\\(?:[0-7]{1,3}|x[0-9a-fA-F]{1,2}|.|$)')
ENCODE_REGEX = re.compile('(?:\\\\|\b|\f|\n|\r|\t|\v)')


def decode_copy_value(value):
    # Test for null values first.
    if value == POSTGRES_COPY_NULL_VALUE:
        return None

    return DECODE_REGEX.sub(_decode_copy_value, value)


def _decode_copy_value(match):
    """
    Decodes value received as part of Postgres `COPY` command.

    :param value: Value to decode.
    :type value: str

    :return: Either None if the value is NULL string, or the given value where
             escape sequences have been decoded from.
    :rtype: str|None
    """
    value = match.group(0)

    index = 0
    length = len(value)
    result = None

    while index < length:
        c = value[index]

        if c != "\\":
            if result is not None:
                result += c
            index += 1
            continue

        if result is None:
            result = value[:index]
        index += 1
        if index >= length:
            raise ValueError("Unterminated escape sequence encountered")
        c = value[index]
        index += 1
        if c == "\\":
            unescaped = c
        elif c == "b":
            unescaped = "\b"
        elif c == "f":
            unescaped = "\f"
        elif c == "n":
            unescaped = "\n"
        elif c == "r":
            unescaped = "\r"
        elif c == "t":
            unescaped = "\t"
        elif c == "v":
            unescaped = "\v"
        elif c == "x":
            end_index = index
            while end_index - index < 2 and\
                    end_index < length and\
                    value[end_index] in string.hexdigits:
                end_index += 1
            unescaped = six.unichr(int(value[index:end_index], 16))
            index = end_index
        elif c in string.octdigits:
            end_index = index
            while end_index - index < 2 and\
                    end_index < length and\
                    value[end_index] in string.octdigits:
                end_index += 1
            unescaped = six.unichr(int(value[(index - 1):end_index], 8))
            index = end_index
        else:
            raise ValueError("Unrecognized escape sequence encountered: %r" % (c,))
        result += unescaped

    if result is not None:
        return result

    # Value didn't contain any escaped characters and can be used as is.
    return value


def encode_copy_value(value):
    if value is None:
        return POSTGRES_COPY_NULL_VALUE

    return ENCODE_REGEX.sub(_encode_copy_value, value)


def _encode_copy_value(match):
    """
    Encodes given value into format suitable for Postgres `COPY` statement.

    :param value: Value to encode.
    :type value: str|None

    :return: Given value encoded into format that is suitable to be used in the
             `COPY` command.
    :rtype: str
    """
    value = match.group(0)

    index = 0
    length = len(value)
    result = None

    while index < length:
        c = value[index]
        index += 1
        if c == "\\":
            escaped = "\\\\"
        elif c == "\b":
            escaped = "\\b"
        elif c == "\f":
            escaped = "\\f"
        elif c == "\n":
            escaped = "\\n"
        elif c == "\r":
            escaped = "\\r"
        elif c == "\t":
            escaped = "\\t"
        elif c == "\v":
            escaped = "\\v"
        else:
            if result is not None:
                result += c
            continue
        if result is None:
            result = value[:(index - 1)]
        result += escaped

    if result is not None:
        return result

    # Given value didn't contain anything which needs to be escaped and can be
    # used as is.
    return value
