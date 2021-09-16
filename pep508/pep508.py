import re
import os
import sys
import platform
import dataclasses
#from operator import *
from packaging.version import parse
from packaging.markers import Variable, Value, Op

from .tokenizer import Tokenizer

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
    return parse_marker_expr(tokens)

def parse_marker_expr(tokens):
    """
    MARKER_EXPR: MARKER_ATOM (BOOLOP + MARKER_ATOM)+
    """
    logging.debug(f'parse_marker_and left side')
    expression = [parse_marker_atom(tokens)]
    logging.debug(f'parse_marker_and left side {expression}')
    while tok := tokens.try_read('BOOLOP'):
        logging.debug('parse_marker_and detected "and"')
        expr_right = parse_marker_atom(tokens)
        logging.debug(f'parse_marker_and right side {expr_right}')
        expression.extend((tok.text, expr_right))
    logging.debug(f'parse_marker_and finished, returning {expression}')
    return expression

def parse_marker_atom(tokens):
    """
    MARKER_ATOM: LPAREN MARKER_EXPR RPAREN | MARKER_ITEM
    """
    if tokens.try_read('LPAREN'):
        marker = parse_marker_expr(tokens)
        logging.debug(f'marker {marker}')
        if not tokens.try_read('RPAREN'):
            tokens.raise_syntax_error('missing closing right parenthesis')
        return marker
    else:
        return parse_marker_item(tokens)

def parse_marker_item(tokens):
    """
    MARKER_ITEM: MARKER_VAR MARKER_OP MARKER_VAR
    """
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
    """
    MARKER_VAR: VARIABLE MARKER_VALUE
    """
    if tokens.match('VARIABLE'):
        logging.debug('parse_marker_var detected VARIABLE')
        return parse_variable(tokens)
    else:
        logging.debug('parse_marker_var detected python_str')
        return parse_python_str(tokens)



def parse_variable(tokens):
    env_var = tokens.read('VARIABLE').text.replace('.', '_')
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
    if tokens.match('QUOTED_STRING'):
        python_str = tokens.read().text.strip("\'\"")
        return Value(str(python_str))
    else:
        tokens.raise_syntax_error('python_str expected, should begin with single or double quote')

def parse_marker_op(tokens):
    if tokens.try_read('IN'):
        logging.debug('parse_marker_op detected "in"')
        return Op('in')
    elif tokens.try_read('NOT'):
        tokens.read('IN')
        logging.debug('parse_marker_op detected "not in"')
        return Op('not in')
    elif tokens.match('OP'):
        logging.debug('parse_marker_op detected version_cmp')
        return Op(tokens.read().text)
    else:
        # after marker_var must follow marker_op
        logging.debug('parse_marker_op detected syntax_error')
        tokens.raise_syntax_error('Failed to parse marker_op. Should be one of "<=, <, !=, ==, >=, >, ~=, ===, not, not in"')

#node = parse_quoted_marker(tokens)
#print(node.eval({}))
