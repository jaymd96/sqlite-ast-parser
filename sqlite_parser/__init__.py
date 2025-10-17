#> # Public API Module
#
# This module defines the **public interface** for the sqlite-ast-parser package.
# It exports the main entry points and key classes that users need to interact with the parser.
#
# ## Primary Functions
#
# The parser provides two main entry points:
#
# 1. **`parse_sql(sql: str) -> List[Statement]`**: The main parsing function that takes SQL
#    text and returns a list of AST statement nodes. This is what most users will call.
#
# 2. **`tokenize_sql(sql: str) -> List[Token]`**: Lower-level function that performs only
#    tokenization, returning a list of tokens without building an AST. Useful for debugging
#    or building custom parsers.
#
# ## Usage Pattern
#
# ```python
# from sqlite_parser import parse_sql
#
# sql = "SELECT id, name FROM users WHERE age > 18"
# statements = parse_sql(sql)
#
# for stmt in statements:
#     # stmt is a SelectStatement node
#     print(stmt.select_core.from_clause)
# ```
#
# ## What's Exported
#
# - **Main API**: `parse_sql`, `tokenize_sql`
# - **Core Classes**: `Lexer`, `Token` (for advanced usage)
# - **All AST Nodes**: Every statement and expression node type (via `*` import)
# - **Error Classes**: For exception handling
# - **Version**: Package version string

"""
SQLite SQL Parser

A complete, production-ready SQLite SQL parser that returns detailed Abstract Syntax Trees (AST).

Example usage:
    from sqlite_parser import parse_sql

    sql = "SELECT id, name FROM users WHERE age > 18"
    ast = parse_sql(sql)

    for statement in ast:
        print(statement)
"""

from .parser import parse_sql, tokenize_sql
from .lexer import Lexer, Token
from .ast_nodes import *
from .errors import (
    ParseError,
    LexerError,
    SyntaxError,
    UnexpectedTokenError,
    UnexpectedEOFError
)

__version__ = "0.1.0"
__all__ = [
    # Main API
    "parse_sql",
    "tokenize_sql",
    # Core classes
    "Lexer",
    "Token",
    # Errors
    "ParseError",
    "LexerError",
    "SyntaxError",
    "UnexpectedTokenError",
    "UnexpectedEOFError",
    # All AST nodes are exported via *
]
