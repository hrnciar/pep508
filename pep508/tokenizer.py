import dataclasses
import re

from packaging.specifiers import Specifier

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
    'AT': r'@',
    'LPAREN': r'\(',
    'RPAREN': r'\)',
    'LBRACKET': r'\[',
    'RBRACKET': r'\]',
    'SEMICOLON': r';',
    'COLON': r',',
    'QUOTED_STRING': re.compile(
        r'''
            ('[^']*')
            |
            ("[^"]*")
        ''',
        re.VERBOSE
    ),
    'OP': r'===|==|~=|!=|<=|>=|<|>',
    'VERSION': re.compile(Specifier._version_regex_str, re.VERBOSE | re.IGNORECASE),
    'SQUOTE': r'\'',
    'DQUOTE': r'\"',
    'BOOLOP': r'or|and',
    'IN': r'in',
    'NOT': r'not',
    'VARIABLE': re.compile(
        r'''
            python_version
            |python_full_version
            |os[._]name
            |sys[._]platform
            |platform_(release|system)
            |platform[._](version|machine|python_implementation)
            |python_implementation
            |implementation_(name|version)
            |extra
        ''',
        re.VERBOSE
    ),
    'URL': r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))',
    'FILE_URL': 'file://[^ ;]*',
    'IDENTIFIER': r'([a-zA-Z0-9]|-|_|\.)+',
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
        yield self._make_token('stringEnd', '')

    def __iter__(self):
        while True:
            token = self.read()
            yield token
            if token.name == 'stringEnd':
                break
