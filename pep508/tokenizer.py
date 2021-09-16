import dataclasses
import re


@dataclasses.dataclass
class Token:
    name: str
    text: str
    position: int

    def matches(self, name=None, text=None):
        if name and self.name != name:
            return False
        if text and self.text != text:
            return False
        return True

    def __str__(self):
        return f'{self.position}\t{self.name}\t{self.text}'


class PackagingSyntaxError(Exception):
    """Parsing failed"""
    def __init__(self, message, position):
        super().__init__(message)
        self.position = position


DEFAULT_RULES = {
    None: r'[ \t]+',  # whitespace: not returned as tokens
    'LPAREN': r'\(',
    'RPAREN': r'\)',
    'SEMICOLON': r';',
    'QUOTED_STRING': r'(\'([\ a-zA-Z0-9\(\)\.{}\-_\*#:;,\/\?\[\]\!\~`@\$%\^\&\=\+\|<>\"])*\')|(\"([\ a-zA-Z0-9\(\)\.{}\-_\*#:;,\/\?\[\]\!\~`@\$%\^\&\=\+\|<>\'])*\")',
    'OP': r'===|==|~=|!=|<=|>=|<|>',
    'SQUOTE': r'\'',
    'DQUOTE': r'\"',
    'BOOLOP': r'or|and',
    'IN': r'in',
    'NOT': r'not',
    'VARIABLE': r'python_version|python_full_version|os_name|sys_platform|platform_release|platform_system|platform_version|platform_machine|platform_python_implementation|implementation_name|implementation_version|extra|os\.name|sys\.platform|platform\.version|platform\.machine|platform\.python_implementation|python_implementation',
}


class Tokenizer:
    """Stream of tokens for a LL(1) parser.

    Provides methods to examine the next token to be read, and to read it
    (advance to the next token).

    Tokenizer objects are also iterable.
    """

    def __init__(self, source, rules=DEFAULT_RULES):
        self.source = source
        self.rules = {
            name: re.compile(pattern)
            for name, pattern in rules.items()
        }
        self.next_token = None
        self.generator = self._tokenize()
        self.position = 0

    def peek(self, *match_args, **match_kwargs):
        """Return the next token to be read"""
        if not self.next_token:
            self.next_token = next(self.generator)
        return self.next_token

    def match(self, *match_args, **match_kwargs):
        """Return True if the next token matches the given arguments"""
        token = self.peek()
        return token.matches(*match_args, **match_kwargs)

    def expect(self, *match_args, **match_kwargs):
        """Raise SyntaxError if the next token doesn't match given arguments"""
        token = self.peek()
        if not token.matches(*match_args, **match_kwargs):
            exp = ' '.join(
                v for v
                in match_args +
                    tuple(f'{k}={v!r}' for k, v in match_kwargs.items())
                if v
            )
            raise self.raise_syntax_error(f'Expected {exp}')
        return token

    def read(self, *match_args, **match_kwargs):
        """Return the next token and advance to the next token

        Raise SyntaxError if the token doesn't match.
        """
        result = self.expect(*match_args, **match_kwargs)
        self.next_token = None
        return result

    def try_read(self, *match_args, **match_kwargs):
        """read() if the next token matches the given arguments

        Do nothing if it does not match.
        """
        if self.match(*match_args, **match_kwargs):
            return self.read()

    def raise_syntax_error(self, message='Invalid marker'):
        """Raise SyntaxError at the given position in the marker"""
        at = f'at position {self.position}:'
        marker = ' ' * self.position + '^'
        raise PackagingSyntaxError(
            f'{message}\n{at}\n    {self.source}\n    {marker}',
            self.position,
        )

    def _make_token(self, name, text):
        """Make a token with the current position"""
        return Token(name, text, self.position)

    def _tokenize(self):
        """The main generator of tokens"""
        while self.position < len(self.source):
            for name, expression in self.rules.items():
                if match := expression.match(self.source, self.position):
                    token_text = match[0]

                    if name:
                        yield self._make_token(name, token_text)
                    self.position += len(token_text)
                    break
            else:
                raise self.raise_syntax_error()
        yield self._make_token('EOF', '')

    def __iter__(self):
        while True:
            token = self.read()
            yield token
            if token.name == 'EOF':
                break
