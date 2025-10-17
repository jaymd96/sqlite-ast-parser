#> # Error Handling System
#
# This module implements a **hierarchical error system** with position tracking for
# providing helpful, context-aware error messages to users.
#
# ## Design Philosophy
#
# Good error messages are critical for usability. This system provides:
#
# 1. **Position Tracking**: Every error knows where it occurred (line and column)
# 2. **Context Display**: Shows the problematic line with a caret (^) pointing to the error
# 3. **Error Hierarchy**: Different error types for different phases (lexing, parsing, semantics)
# 4. **Inheritance**: All errors inherit from `ParseError` for easy catching
#
# ## Error Hierarchy
#
# ```
# ParseError (base)
# ├── LexerError (tokenization errors)
# │   └── InvalidTokenError
# ├── SyntaxError (parsing errors)
# │   ├── UnexpectedTokenError
# │   └── UnexpectedEOFError
# └── SemanticError (context-sensitive errors)
# ```

"""
Error Classes for SQLite SQL Parser

Provides comprehensive error handling with position tracking and
helpful error messages.
"""

from typing import Optional
from .ast_nodes import Position, Span

#> ## Base Error Class
#
# `ParseError` is the **foundation** of the error system. All parser errors inherit from it,
# providing consistent error formatting and position tracking across the entire parser.
#
# ### Key Features
#
# - Stores `position` (line/column), `span` (start/end), and original `sql` text
# - The `format_error()` method creates user-friendly error messages with context:
#
# ```
# Line 5, Column 10: Expected SELECT, found INSERT
# SELECT * FORM users
#          ^
# ```
#
# Notice the typo "FORM" instead of "FROM" - the caret points exactly to the error location.

class ParseError(Exception):
    """Base class for all parsing errors"""

    def __init__(self, message: str, position: Optional[Position] = None,
                 span: Optional[Span] = None, sql: Optional[str] = None):
        self.message = message
        self.position = position
        self.span = span
        self.sql = sql
        super().__init__(self.format_error())

    def format_error(self) -> str:
        """Format error message with context"""
        result = self.message

        if self.position:
            result = f"Line {self.position.line}, Column {self.position.column}: {result}"

        if self.sql and self.position:
            # Show snippet of SQL around error
            lines = self.sql.split('\n')
            if 0 <= self.position.line - 1 < len(lines):
                error_line = lines[self.position.line - 1]
                result += f"\n{error_line}\n"
                result += " " * (self.position.column - 1) + "^"

        return result

#> ## Lexer Errors
#
# `LexerError` represents problems during **tokenization** - the first phase of parsing.
# These occur when the lexer encounters invalid characters or malformed tokens.
#
# ### Example Scenarios
#
# - Invalid escape sequences in strings
# - Unclosed string literals
# - Invalid hex digits in BLOB literals
# - Illegal characters not part of SQL syntax

class LexerError(ParseError):
    """Error during tokenization"""
    pass

#> ## Syntax Errors
#
# `SyntaxError` represents problems during **parsing** - when tokens are valid but
# arranged in an invalid grammar structure.
#
# This is the most common error type, raised when the parser encounters unexpected
# tokens or missing required syntax elements.

class SyntaxError(ParseError):
    """Syntax error during parsing"""
    pass

#> ### Unexpected Token Error
#
# `UnexpectedTokenError` is raised when the parser expects one token type but finds another.
# This is the **workhorse** of syntax error reporting.
#
# ### Example
#
# ```python
# Expected TokenType.FROM, found TokenType.WHERE
# ```
#
# The parser maintains the expected and found values for detailed error messages and
# potential error recovery in the future.

class UnexpectedTokenError(SyntaxError):
    """Unexpected token encountered"""

    def __init__(self, expected: str, found: str,
                 position: Optional[Position] = None,
                 span: Optional[Span] = None, sql: Optional[str] = None):
        message = f"Expected {expected}, found {found}"
        super().__init__(message, position, span, sql)
        self.expected = expected
        self.found = found

#> ### Unexpected EOF Error
#
# `UnexpectedEOFError` is raised when the parser reaches the **end of input** while still
# expecting more tokens.
#
# ### Example Scenarios
#
# - `SELECT * FROM` (missing table name)
# - `CREATE TABLE users (` (unclosed parenthesis)
# - `BEGIN TRANSACTION` (missing statement after transaction start)
#
# This is a special case of unexpected token where the "found" token is always EOF.

class UnexpectedEOFError(SyntaxError):
    """Unexpected end of input"""

    def __init__(self, expected: str, position: Optional[Position] = None,
                 sql: Optional[str] = None):
        message = f"Unexpected end of input, expected {expected}"
        super().__init__(message, position, None, sql)

#> ### Invalid Token Error
#
# `InvalidTokenError` is a specific `LexerError` for **malformed tokens** that can't
# be recovered from. This is rarer than syntax errors because the lexer is quite
# permissive (most invalid SQL will tokenize successfully, then fail during parsing).

class InvalidTokenError(LexerError):
    """Invalid token in input"""
    pass

#> ## Semantic Errors
#
# `SemanticError` represents **context-sensitive errors** that aren't purely syntactic.
# These require understanding the meaning of the SQL, not just its structure.
#
# ### Example Scenarios (not yet implemented)
#
# - Using a column name that doesn't exist
# - Type mismatches in expressions
# - Invalid function argument counts
# - Ambiguous column references
#
# Currently this class exists as a placeholder for future semantic analysis features.

class SemanticError(ParseError):
    """Semantic error (context-sensitive)"""
    pass
