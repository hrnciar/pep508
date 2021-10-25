import os
import sys
import platform
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

def parse_named_requirement(requirement):
    """
    NAMED_REQUIREMENT: NAME EXTRAS* URL* (SEMICOLON + MARKER)*
    """
    tokens = Tokenizer(requirement)
    name = parse_identifier(tokens)
    extras = parse_extras(tokens)
    specifier = ""
    url = ""
    if tokens.match('AT'):
        url = parse_url(tokens)
    elif not tokens.match('stringEnd'):
        specifier = parse_specifier(tokens)
    if tokens.match('SEMICOLON'):
        marker = ""
        while not tokens.match('stringEnd'):
            # NOTE: we don't validate markers here, it's done later as part of
            # packaging/requirements.py
            marker += tokens.read().text
    else:
        marker = None
        tokens.expect('stringEnd')
    return (name, url, extras, specifier, marker)

def parse_extras(tokens):
    """
    EXTRAS: (LBRACKET + IDENTIFIER + (COLON + IDENTIFIER)* + RBRACKET)*
    """
    extras = []
    if tokens.try_read('LBRACKET'):
        while tokens.match('IDENTIFIER'):
            extras.append(parse_identifier(tokens))
            tokens.try_read('COLON')
        if not tokens.try_read('RBRACKET'):
            tokens.raise_syntax_error('Left bracket is present, but the right bracket is missing')
    return extras

def parse_url(tokens):
    """
    URL: AT (URL | FILE_URL)
    """
    tokens.read('AT')
    if tokens.match('URL') or tokens.match('FILE_URL'):
        return tokens.read().text
    else:
        tokens.raise_syntax_error('Invalid URL: ')

def parse_identifier(tokens):
    if tokens.match('IDENTIFIER'):
        return tokens.read().text.strip("\'\"")
    else:
        #TODO: tests used to fail when this was raised
        # Requirement should begin with identifier thus this should raise an
        # error if 'IDENTIFIER' token wasn't matched.
        # Original implementation allowed to test substrings of Requirement.
        # For example, Requirement in test_url begins with 'AT' token and
        # therefore it fails here.
        # I don't know if it is important to preserve former behavior, if not,
        # I would just keep the fixed test as I did in
        # https://github.com/hrnciar/packaging/commit/88586e8201a3db39eadebbc857906a3c3c6ae96f#diff-08805c14255c1d694b99cbec5e5c4c6f2c6eca41c860e1a1c5fb9b353e0c6eb6L82
        tokens.raise_syntax_error('Expected IDENTIFIER token wasn\'t found')

def parse_specifier(tokens):
    """
    SPECIFIER: LPAREN (OP + VERSION + COLON)+ RPAREN | OP + VERSION
    """
    parsed_specifiers = ""
    lparen = False
    if tokens.try_read('LPAREN'):
        lparen = True
    while tokens.match('OP'):
        parsed_specifiers += tokens.read('OP').text
        if tokens.match('VERSION'):
            parsed_specifiers += tokens.read('VERSION').text
        else:
            tokens.raise_syntax_error('Missing version')
        if tokens.match('COLON'):
            parsed_specifiers += tokens.read('COLON').text
    if lparen and not tokens.try_read('RPAREN'):
        tokens.raise_syntax_error('Left parent is present, but the right parent is missing')
    return parsed_specifiers

def parse_quoted_marker(tokens):
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
