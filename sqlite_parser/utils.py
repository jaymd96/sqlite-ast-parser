#> # Utility Functions and Constants
#
# This module serves as the **foundation** of the SQLite parser, providing all the essential
# constants, enumerations, and lookup tables needed for tokenization and parsing.
#
# ## Key Components
#
# 1. **TokenType Enum**: Defines all 200+ token types including SQLite's 147 keywords,
#    operators, delimiters, and literals
# 2. **Keyword Mapping**: Fast O(1) lookup from string to token type
# 3. **Precedence Table**: Defines operator precedence for expression parsing
# 4. **Operator Mappings**: Convert tokens to AST operator nodes
# 5. **Helper Functions**: Common operations like keyword checking and precedence lookup
#
# The design follows **separation of concerns**: this module contains only static data and
# pure functions, with no parsing or lexing logic.

"""
Utility Functions and Constants for SQLite SQL Parser

Contains keyword lists, precedence tables, and helper functions.
"""

from enum import Enum, auto
from typing import Dict, Set
from .ast_nodes import BinaryOperator, UnaryOperator

#> ## Token Type Enumeration
#
# The `TokenType` enum is the parser's **vocabulary**. It defines every distinct type of token
# that can appear in SQLite SQL, organized into logical categories:
#
# - **Keywords** (lines 15-168): All 147 SQLite reserved words plus TRUE/FALSE
# - **Operators** (lines 170-191): Arithmetic, comparison, bitwise, and special operators
# - **Delimiters** (lines 193-200): Parentheses, brackets, commas, and punctuation
# - **Literals** (lines 202-207): Numbers, strings, blobs, identifiers, and parameters
# - **Special** (lines 209-211): EOF and NEWLINE for parser control flow
#
# Using Python's `auto()` generates sequential integer values automatically, making it easy
# to add new token types without manual numbering.

class TokenType(Enum):
    """Token types for SQLite SQL"""
    # Keywords (147 SQLite keywords)
    ABORT = auto()
    ACTION = auto()
    ADD = auto()
    AFTER = auto()
    ALL = auto()
    ALTER = auto()
    ALWAYS = auto()
    ANALYZE = auto()
    AND = auto()
    AS = auto()
    ASC = auto()
    ATTACH = auto()
    AUTOINCREMENT = auto()
    BEFORE = auto()
    BEGIN = auto()
    BETWEEN = auto()
    BY = auto()
    CASCADE = auto()
    CASE = auto()
    CAST = auto()
    CHECK = auto()
    COLLATE = auto()
    COLUMN = auto()
    COMMIT = auto()
    CONFLICT = auto()
    CONSTRAINT = auto()
    CREATE = auto()
    CROSS = auto()
    CURRENT = auto()
    CURRENT_DATE = auto()
    CURRENT_TIME = auto()
    CURRENT_TIMESTAMP = auto()
    DATABASE = auto()
    DEFAULT = auto()
    DEFERRABLE = auto()
    DEFERRED = auto()
    DELETE = auto()
    DESC = auto()
    DETACH = auto()
    DISTINCT = auto()
    DO = auto()
    DROP = auto()
    EACH = auto()
    ELSE = auto()
    END = auto()
    ESCAPE = auto()
    EXCEPT = auto()
    EXCLUDE = auto()
    EXCLUSIVE = auto()
    EXISTS = auto()
    EXPLAIN = auto()
    FAIL = auto()
    FILTER = auto()
    FIRST = auto()
    FOLLOWING = auto()
    FOR = auto()
    FOREIGN = auto()
    FROM = auto()
    FULL = auto()
    GENERATED = auto()
    GLOB = auto()
    GROUP = auto()
    GROUPS = auto()
    HAVING = auto()
    IF = auto()
    IGNORE = auto()
    IMMEDIATE = auto()
    IN = auto()
    INDEX = auto()
    INDEXED = auto()
    INITIALLY = auto()
    INNER = auto()
    INSERT = auto()
    INSTEAD = auto()
    INTERSECT = auto()
    INTO = auto()
    IS = auto()
    ISNULL = auto()
    JOIN = auto()
    KEY = auto()
    LAST = auto()
    LEFT = auto()
    LIKE = auto()
    LIMIT = auto()
    MATCH = auto()
    MATERIALIZED = auto()
    NATURAL = auto()
    NO = auto()
    NOT = auto()
    NOTHING = auto()
    NOTNULL = auto()
    NULL = auto()
    NULLS = auto()
    OF = auto()
    OFFSET = auto()
    ON = auto()
    OR = auto()
    ORDER = auto()
    OTHERS = auto()
    OUTER = auto()
    OVER = auto()
    PARTITION = auto()
    PLAN = auto()
    PRAGMA = auto()
    PRECEDING = auto()
    PRIMARY = auto()
    QUERY = auto()
    RAISE = auto()
    RANGE = auto()
    RECURSIVE = auto()
    REFERENCES = auto()
    REGEXP = auto()
    REINDEX = auto()
    RELEASE = auto()
    RENAME = auto()
    REPLACE = auto()
    RESTRICT = auto()
    RETURNING = auto()
    RIGHT = auto()
    ROLLBACK = auto()
    ROW = auto()
    ROWID = auto()
    ROWS = auto()
    SAVEPOINT = auto()
    SELECT = auto()
    SET = auto()
    STRICT = auto()
    STORED = auto()
    TABLE = auto()
    TEMP = auto()
    TEMPORARY = auto()
    THEN = auto()
    TIES = auto()
    TO = auto()
    TRANSACTION = auto()
    TRIGGER = auto()
    UNBOUNDED = auto()
    UNION = auto()
    UNIQUE = auto()
    UPDATE = auto()
    USING = auto()
    VACUUM = auto()
    VALUES = auto()
    VIEW = auto()
    VIRTUAL = auto()
    WHEN = auto()
    WHERE = auto()
    WINDOW = auto()
    WITH = auto()
    WITHOUT = auto()

    # Special keywords
    TRUE = auto()
    FALSE = auto()

    # Operators
    PLUS = auto()              # +
    MINUS = auto()             # -
    STAR = auto()              # *
    SLASH = auto()             # /
    PERCENT = auto()           # %
    CONCAT = auto()            # ||
    EQUAL = auto()             # =
    EQUAL2 = auto()            # ==
    NOT_EQUAL = auto()         # !=
    NOT_EQUAL2 = auto()        # <>
    LESS = auto()              # <
    GREATER = auto()           # >
    LESS_EQUAL = auto()        # <=
    GREATER_EQUAL = auto()     # >=
    LEFT_SHIFT = auto()        # <<
    RIGHT_SHIFT = auto()       # >>
    AMPERSAND = auto()         # &
    PIPE = auto()              # |
    TILDE = auto()             # ~
    ARROW = auto()             # ->
    DOUBLE_ARROW = auto()      # ->>

    # Delimiters
    LPAREN = auto()            # (
    RPAREN = auto()            # )
    LBRACKET = auto()          # [
    RBRACKET = auto()          # ]
    COMMA = auto()             # ,
    SEMICOLON = auto()         # ;
    DOT = auto()               # .

    # Literals
    NUMBER = auto()            # 123, 123.45, 1.5e10
    STRING = auto()            # 'string'
    BLOB = auto()              # X'hex'
    IDENTIFIER = auto()        # name, [name], "name", `name`
    PARAMETER = auto()         # ?, ?123, :name, @name, $name

    # Special
    EOF = auto()
    NEWLINE = auto()

#> ## Keyword Lookup Dictionary
#
# The `KEYWORDS` dictionary provides **O(1) lookup** from uppercase string to TokenType.
# This is used during lexing to distinguish keywords from identifiers.
#
# ### Design Decisions
#
# - **Case insensitivity**: All keys are uppercase because SQLite keywords are case-insensitive.
#   The lexer normalizes input before lookup.
# - **Complete coverage**: Includes all 147 official SQLite keywords from the
#   [SQLite documentation](https://sqlite.org/lang_keywords.html)
# - **Easy maintenance**: The 1:1 mapping from string to enum makes it trivial to add new keywords
#
# When the lexer encounters an identifier, it checks `KEYWORDS` to determine if it's actually
# a reserved word.

# Map keyword strings to token types
KEYWORDS: Dict[str, TokenType] = {
    'ABORT': TokenType.ABORT,
    'ACTION': TokenType.ACTION,
    'ADD': TokenType.ADD,
    'AFTER': TokenType.AFTER,
    'ALL': TokenType.ALL,
    'ALTER': TokenType.ALTER,
    'ALWAYS': TokenType.ALWAYS,
    'ANALYZE': TokenType.ANALYZE,
    'AND': TokenType.AND,
    'AS': TokenType.AS,
    'ASC': TokenType.ASC,
    'ATTACH': TokenType.ATTACH,
    'AUTOINCREMENT': TokenType.AUTOINCREMENT,
    'BEFORE': TokenType.BEFORE,
    'BEGIN': TokenType.BEGIN,
    'BETWEEN': TokenType.BETWEEN,
    'BY': TokenType.BY,
    'CASCADE': TokenType.CASCADE,
    'CASE': TokenType.CASE,
    'CAST': TokenType.CAST,
    'CHECK': TokenType.CHECK,
    'COLLATE': TokenType.COLLATE,
    'COLUMN': TokenType.COLUMN,
    'COMMIT': TokenType.COMMIT,
    'CONFLICT': TokenType.CONFLICT,
    'CONSTRAINT': TokenType.CONSTRAINT,
    'CREATE': TokenType.CREATE,
    'CROSS': TokenType.CROSS,
    'CURRENT': TokenType.CURRENT,
    'CURRENT_DATE': TokenType.CURRENT_DATE,
    'CURRENT_TIME': TokenType.CURRENT_TIME,
    'CURRENT_TIMESTAMP': TokenType.CURRENT_TIMESTAMP,
    'DATABASE': TokenType.DATABASE,
    'DEFAULT': TokenType.DEFAULT,
    'DEFERRABLE': TokenType.DEFERRABLE,
    'DEFERRED': TokenType.DEFERRED,
    'DELETE': TokenType.DELETE,
    'DESC': TokenType.DESC,
    'DETACH': TokenType.DETACH,
    'DISTINCT': TokenType.DISTINCT,
    'DO': TokenType.DO,
    'DROP': TokenType.DROP,
    'EACH': TokenType.EACH,
    'ELSE': TokenType.ELSE,
    'END': TokenType.END,
    'ESCAPE': TokenType.ESCAPE,
    'EXCEPT': TokenType.EXCEPT,
    'EXCLUDE': TokenType.EXCLUDE,
    'EXCLUSIVE': TokenType.EXCLUSIVE,
    'EXISTS': TokenType.EXISTS,
    'EXPLAIN': TokenType.EXPLAIN,
    'FAIL': TokenType.FAIL,
    'FILTER': TokenType.FILTER,
    'FIRST': TokenType.FIRST,
    'FOLLOWING': TokenType.FOLLOWING,
    'FOR': TokenType.FOR,
    'FOREIGN': TokenType.FOREIGN,
    'FROM': TokenType.FROM,
    'FULL': TokenType.FULL,
    'GENERATED': TokenType.GENERATED,
    'GLOB': TokenType.GLOB,
    'GROUP': TokenType.GROUP,
    'GROUPS': TokenType.GROUPS,
    'HAVING': TokenType.HAVING,
    'IF': TokenType.IF,
    'IGNORE': TokenType.IGNORE,
    'IMMEDIATE': TokenType.IMMEDIATE,
    'IN': TokenType.IN,
    'INDEX': TokenType.INDEX,
    'INDEXED': TokenType.INDEXED,
    'INITIALLY': TokenType.INITIALLY,
    'INNER': TokenType.INNER,
    'INSERT': TokenType.INSERT,
    'INSTEAD': TokenType.INSTEAD,
    'INTERSECT': TokenType.INTERSECT,
    'INTO': TokenType.INTO,
    'IS': TokenType.IS,
    'ISNULL': TokenType.ISNULL,
    'JOIN': TokenType.JOIN,
    'KEY': TokenType.KEY,
    'LAST': TokenType.LAST,
    'LEFT': TokenType.LEFT,
    'LIKE': TokenType.LIKE,
    'LIMIT': TokenType.LIMIT,
    'MATCH': TokenType.MATCH,
    'MATERIALIZED': TokenType.MATERIALIZED,
    'NATURAL': TokenType.NATURAL,
    'NO': TokenType.NO,
    'NOT': TokenType.NOT,
    'NOTHING': TokenType.NOTHING,
    'NOTNULL': TokenType.NOTNULL,
    'NULL': TokenType.NULL,
    'NULLS': TokenType.NULLS,
    'OF': TokenType.OF,
    'OFFSET': TokenType.OFFSET,
    'ON': TokenType.ON,
    'OR': TokenType.OR,
    'ORDER': TokenType.ORDER,
    'OTHERS': TokenType.OTHERS,
    'OUTER': TokenType.OUTER,
    'OVER': TokenType.OVER,
    'PARTITION': TokenType.PARTITION,
    'PLAN': TokenType.PLAN,
    'PRAGMA': TokenType.PRAGMA,
    'PRECEDING': TokenType.PRECEDING,
    'PRIMARY': TokenType.PRIMARY,
    'QUERY': TokenType.QUERY,
    'RAISE': TokenType.RAISE,
    'RANGE': TokenType.RANGE,
    'RECURSIVE': TokenType.RECURSIVE,
    'REFERENCES': TokenType.REFERENCES,
    'REGEXP': TokenType.REGEXP,
    'REINDEX': TokenType.REINDEX,
    'RELEASE': TokenType.RELEASE,
    'RENAME': TokenType.RENAME,
    'REPLACE': TokenType.REPLACE,
    'RESTRICT': TokenType.RESTRICT,
    'RETURNING': TokenType.RETURNING,
    'RIGHT': TokenType.RIGHT,
    'ROLLBACK': TokenType.ROLLBACK,
    'ROW': TokenType.ROW,
    'ROWID': TokenType.ROWID,
    'ROWS': TokenType.ROWS,
    'SAVEPOINT': TokenType.SAVEPOINT,
    'SELECT': TokenType.SELECT,
    'SET': TokenType.SET,
    'STORED': TokenType.STORED,
    'STRICT': TokenType.STRICT,
    'TABLE': TokenType.TABLE,
    'TEMP': TokenType.TEMP,
    'TEMPORARY': TokenType.TEMPORARY,
    'THEN': TokenType.THEN,
    'TIES': TokenType.TIES,
    'TO': TokenType.TO,
    'TRANSACTION': TokenType.TRANSACTION,
    'TRIGGER': TokenType.TRIGGER,
    'UNBOUNDED': TokenType.UNBOUNDED,
    'UNION': TokenType.UNION,
    'UNIQUE': TokenType.UNIQUE,
    'UPDATE': TokenType.UPDATE,
    'USING': TokenType.USING,
    'VACUUM': TokenType.VACUUM,
    'VALUES': TokenType.VALUES,
    'VIEW': TokenType.VIEW,
    'VIRTUAL': TokenType.VIRTUAL,
    'WHEN': TokenType.WHEN,
    'WHERE': TokenType.WHERE,
    'WINDOW': TokenType.WINDOW,
    'WITH': TokenType.WITH,
    'WITHOUT': TokenType.WITHOUT,
    'TRUE': TokenType.TRUE,
    'FALSE': TokenType.FALSE,
}

#> ## Operator Precedence Table
#
# The `PRECEDENCE` dictionary defines the **parsing priority** for binary operators.
# Lower numbers bind less tightly (evaluate later), following the **precedence climbing**
# algorithm used in expression parsing.
#
# ### Precedence Levels (from lowest to highest)
#
# 1. **OR** (1): Logical OR - lowest precedence, binds loosest
# 2. **AND** (2): Logical AND
# 3. **NOT** (3): Logical negation (unary, but listed here for reference)
# 4. **Comparison** (4): `=`, `<`, `>`, `IS`, `IN`, `LIKE`, `BETWEEN`, etc.
# 5. **Bitwise** (5): Bit shifts and bitwise AND/OR
# 6. **Additive** (6): `+`, `-`, `||` (string concatenation)
# 7. **Multiplicative** (7): `*`, `/`, `%` - highest precedence, binds tightest
#
# ### Example
#
# In `1 + 2 * 3 OR 4 < 5 AND 6`:
# - `2 * 3` evaluates first (precedence 7)
# - `1 + 6` follows (precedence 6)
# - `4 < 5` comparison (precedence 4)
# - `AND` (precedence 2)
# - `OR` (precedence 1) last
#
# **Note**: Special operators like `BETWEEN`, `IN`, and `LIKE` have their own parsing methods,
# but are listed here at precedence 4 for when they appear as binary operators.

# Operator precedence (lower number = lower precedence)
PRECEDENCE: Dict[TokenType, int] = {
    TokenType.OR: 1,
    TokenType.AND: 2,
    TokenType.NOT: 3,
    # Comparison operators
    TokenType.EQUAL: 4,
    TokenType.EQUAL2: 4,
    TokenType.NOT_EQUAL: 4,
    TokenType.NOT_EQUAL2: 4,
    TokenType.LESS: 4,
    TokenType.GREATER: 4,
    TokenType.LESS_EQUAL: 4,
    TokenType.GREATER_EQUAL: 4,
    TokenType.IS: 4,
    TokenType.IN: 4,
    TokenType.LIKE: 4,
    TokenType.GLOB: 4,
    TokenType.MATCH: 4,
    TokenType.REGEXP: 4,
    TokenType.BETWEEN: 4,
    # Bitwise
    TokenType.LEFT_SHIFT: 5,
    TokenType.RIGHT_SHIFT: 5,
    TokenType.AMPERSAND: 5,
    TokenType.PIPE: 5,
    # Arithmetic and string
    TokenType.PLUS: 6,
    TokenType.MINUS: 6,
    TokenType.CONCAT: 6,
    TokenType.STAR: 7,
    TokenType.SLASH: 7,
    TokenType.PERCENT: 7,
    # COLLATE handled specially
    # Unary handled specially
}

#> ## Associativity
#
# SQL operators are **left-associative** by default, meaning `a - b - c` parses as `(a - b) - c`.
# This empty set is a placeholder for any right-associative operators that might be added in
# the future (though SQL has very few right-associative operators).

# Right-associative operators
RIGHT_ASSOCIATIVE: Set[TokenType] = set()  # Most operators in SQL are left-associative

#> ## Helper Functions
#
# These utility functions provide **clean abstractions** over the lookup tables, making
# the lexer and parser code more readable and maintainable.
#
# Each function has a single, clear responsibility:
# - Keyword checking and normalization
# - Operator classification and precedence lookup
# - Token-to-AST-node conversion

def is_keyword(word: str) -> bool:
    """Check if a word is a SQLite keyword"""
    return word.upper() in KEYWORDS


def normalize_keyword(word: str) -> str:
    """Normalize keyword to uppercase"""
    return word.upper()


def get_keyword_token_type(word: str) -> TokenType:
    """Get token type for keyword"""
    return KEYWORDS.get(word.upper(), TokenType.IDENTIFIER)


def is_binary_operator(token_type: TokenType) -> bool:
    """Check if token type is a binary operator"""
    return token_type in PRECEDENCE


def get_precedence(token_type: TokenType) -> int:
    """Get precedence for operator"""
    return PRECEDENCE.get(token_type, 0)


def is_right_associative(token_type: TokenType) -> bool:
    """Check if operator is right-associative"""
    return token_type in RIGHT_ASSOCIATIVE

#> ## Token-to-AST Operator Mappings
#
# These dictionaries convert **TokenTypes** to **AST operator enums**, bridging the gap
# between the lexer (which produces tokens) and the parser (which builds AST nodes).
#
# ### Binary Operators
#
# Maps operator tokens to `BinaryOperator` enum values. For example, when the parser
# sees a `TokenType.PLUS` token, it converts it to `BinaryOperator.ADD` for the AST node.
#
# This separation allows the same token type to map to different operators in different
# contexts (though SQL doesn't often need this flexibility).

# Token type to binary operator mapping
TOKEN_TO_BINARY_OP: Dict[TokenType, BinaryOperator] = {
    TokenType.PLUS: BinaryOperator.ADD,
    TokenType.MINUS: BinaryOperator.SUBTRACT,
    TokenType.STAR: BinaryOperator.MULTIPLY,
    TokenType.SLASH: BinaryOperator.DIVIDE,
    TokenType.PERCENT: BinaryOperator.MODULO,
    TokenType.EQUAL: BinaryOperator.EQUAL,
    TokenType.EQUAL2: BinaryOperator.EQUAL2,
    TokenType.NOT_EQUAL: BinaryOperator.NOT_EQUAL,
    TokenType.NOT_EQUAL2: BinaryOperator.NOT_EQUAL2,
    TokenType.LESS: BinaryOperator.LESS_THAN,
    TokenType.GREATER: BinaryOperator.GREATER_THAN,
    TokenType.LESS_EQUAL: BinaryOperator.LESS_EQUAL,
    TokenType.GREATER_EQUAL: BinaryOperator.GREATER_EQUAL,
    TokenType.AND: BinaryOperator.AND,
    TokenType.OR: BinaryOperator.OR,
    TokenType.AMPERSAND: BinaryOperator.BIT_AND,
    TokenType.PIPE: BinaryOperator.BIT_OR,
    TokenType.LEFT_SHIFT: BinaryOperator.LEFT_SHIFT,
    TokenType.RIGHT_SHIFT: BinaryOperator.RIGHT_SHIFT,
    TokenType.CONCAT: BinaryOperator.CONCAT,
    TokenType.IS: BinaryOperator.IS,
    TokenType.IN: BinaryOperator.IN,
    TokenType.LIKE: BinaryOperator.LIKE,
    TokenType.GLOB: BinaryOperator.GLOB,
    TokenType.MATCH: BinaryOperator.MATCH,
    TokenType.REGEXP: BinaryOperator.REGEXP,
}

#> ### Unary Operators
#
# Maps unary operator tokens to `UnaryOperator` enum values. Unary operators appear before
# their operand (prefix position): `-5`, `NOT condition`, `~bitmask`.
#
# Note that `+` and `-` can be both unary and binary operators. The parser determines which
# based on context (whether there's a left operand).

# Token type to unary operator mapping
TOKEN_TO_UNARY_OP: Dict[TokenType, UnaryOperator] = {
    TokenType.PLUS: UnaryOperator.PLUS,
    TokenType.MINUS: UnaryOperator.MINUS,
    TokenType.NOT: UnaryOperator.NOT,
    TokenType.TILDE: UnaryOperator.BITNOT,
}
