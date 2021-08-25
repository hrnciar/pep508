import re
import os
import sys
import platform
import dataclasses
#from operator import *
from packaging.version import parse
from packaging.markers import Variable, Value, Op

from .tokenizer import Tokenizer
from .my_ast import SimpleAssignment, String, BinOp

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

def default_environment():
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }

def format_full_version(info):
    version = '{0.major}.{0.minor}.{0.micro}'.format(info)
    kind = info.releaselevel
    if kind != 'final':
        version += kind[0] + str(info.serial)
    return version

if hasattr(sys, 'implementation'):
    implementation_version = format_full_version(sys.implementation.version)
else:
    implementation_version = "0"

def parse_quoted_marker(tokens):
    #TODO: consume everything until first ";"
    tokens.try_read('SEMICOLON')
    logging.debug('read ";", attempting to read marker')
    while tokens.try_read('WSP'):
        pass
    return parse_marker_or(tokens)

def parse_marker_or(tokens):
    logging.debug('parse_marker_or left side')
    marker_and_left = parse_marker_and(tokens)
    while tokens.try_read('WSP'):
        pass
    if tokens.try_read('OR'):
        marker_and_right = parse_marker_and(tokens)
        return [marker_and_left, 'or', marker_and_right]
    else:
        logging.debug('parse_marker_or finished, returning left side')
        return [marker_and_left]

def parse_marker_and(tokens):
    logging.debug(f'parse_marker_and left side')
    marker_expr_left = parse_marker_expr(tokens)
    logging.debug(f'parse_marker_and left side {marker_expr_left}')
    while tokens.try_read('WSP'):
        pass
    # if next token is OR, we parsed left part of marker_or and we have to
    # continue with parsing in parse_marker_or()
    if tokens.match('OR'):
        return marker_expr_left
    if tokens.try_read('AND'):
        logging.debug('parse_marker_and detected "and"')
        marker_expr_right = parse_marker_expr(tokens)
        logging.debug(f'parse_marker_and right side {marker_expr_right}')
        logging.debug(('and', marker_expr_left, marker_expr_right))
        return [marker_expr_left, 'and', marker_expr_right]
    else:
        logging.debug(f'parse_marker_and finished, returning left side {marker_expr_left}')
        return [marker_expr_left]

def parse_marker_expr(tokens):
    while tokens.try_read('WSP'):
        pass
    if tokens.try_read('LPAREN'):
        marker = parse_marker_or(tokens)
        logging.debug(f'marker {marker}')
        if not tokens.try_read('RPAREN'):
            tokens.raise_syntax_error('missing closing right parenthesis')
        return marker
    else:
        logging.debug('parse_marker_expr no other marker')
        marker_var_left = parse_marker_var(tokens)
        logging.debug(f'parse_marker_var left side {marker_var_left}')
        marker_op = parse_marker_op(tokens)
        logging.debug(f'parse_marker_var op {marker_op}')
        marker_var_right = parse_marker_var(tokens)
        logging.debug(f'parse_marker_var right side {marker_var_right}')
        return (marker_var_left, marker_op, marker_var_right)

# TODO:
#ops = {
#    '<': operator.lt,
#    'in': operator.contains,
#}
# ops['<']('12', '34')

def parse_marker_var(tokens):
    while tokens.try_read('WSP'):
        pass
    if tokens.match('ENV_VAR'):
        logging.debug('parse_marker_var detected ENV_VAR')
        return parse_env_var(tokens)
    else:
        logging.debug('parse_marker_var detected python_str')
        return parse_python_str(tokens)



def parse_env_var(tokens):
    env_var = tokens.read('ENV_VAR').text.replace('.', '_')
    if env_var == 'platform_python_implementation' or env_var == 'python_implementation':
        return Variable('platform_python_implementation')
        #return String(str(python_str))
    elif env_var == 'platform_python_version':
        return Variable('python_full_version')
    elif env_var == 'sys_implementation.name':
        return Variable('implementation_name')
    #elif env_var == 'extra':
    #    try:
    #        return SimpleAssignment(env_var, tokens.environment['extra'])
    #    except KeyError:
    #        from packaging.markers import UndefinedEnvironmentName
    #        raise UndefinedEnvironmentName()
    else:
        return Variable(env_var)

def parse_python_str(tokens):
    while tokens.try_read('WSP'):
        pass
    if tokens.match('PYTHON_STR'):
        python_str = tokens.read().text.strip("\'\"")
        return Value(str(python_str))
    else:
        tokens.raise_syntax_error('python_str expected, should begin with single or double quote')

def parse_marker_op(tokens):
    while tokens.try_read('WSP'):
        pass
    if tokens.try_read('IN'):
        logging.debug('parse_marker_op detected "in"')
        return Op('in')
    elif tokens.try_read('NOT'):
        tokens.expect('WSP')
        while tokens.try_read('WSP'):
            pass
        tokens.expect('IN')
        tokens.read('IN')
        while tokens.try_read('WSP'):
            pass
        logging.debug('parse_marker_op detected "not in"')
        return Op('not in')
    elif tokens.match('OP'):
        logging.debug('parse_marker_op detected version_cmp')
        return Op(tokens.read().text)
    else:
        # after marker_var must follow marker_op
        logging.debug('parse_marker_op detected syntax_error')
        from packaging.markers import InvalidMarker
        raise InvalidMarker('Failed to parse marker_op. Should be one of "<=, <, !=, ==, >=, >, ~=, ===, not, not in"')

#node = parse_quoted_marker(tokens)
#my_ast.dump(node)
#print(node.eval({}))
