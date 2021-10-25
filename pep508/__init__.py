#from .pep508 import parse_quoted_marker
#from .tokenizer import Tokenizer
#from .my_ast import *

#__all__ = ['parse_quoted_marker', 'Tokenizer']

from pep508.pep508 import parse_quoted_marker, parse_named_requirement
from pep508.tokenizer import Tokenizer, PackagingSyntaxError

__all__ = ['parse_quoted_marker', 'Tokenizer', 'String', 'BinOp', 'SimpleAssignment', 'PackagingSyntaxError']
