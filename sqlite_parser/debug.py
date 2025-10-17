#> # Debugging Utilities
#
# This module provides **comprehensive debugging tools** for inspecting parser internals.
# These utilities are invaluable when developing new parser features or diagnosing issues.
#
# ## Debugging Capabilities
#
# 1. **Token Stream Visualization**: Pretty-print tokens with optional highlighting
# 2. **AST Formatting**: Hierarchical display of AST node trees
# 3. **Parser Tracing**: Log parser method calls and decisions
# 4. **State Inspection**: View parser state at any point
# 5. **Context Managers**: Temporarily enable debugging
# 6. **High-Level Debug Parse**: One-function debugging workflow
#
# ## Usage Patterns
#
# ### Quick Debugging
#
# ```python
# from sqlite_parser.debug import debug_parse
#
# # Parse with full tracing
# statements = debug_parse("SELECT * FROM users", verbose=True)
# ```
#
# ### Detailed Token Inspection
#
# ```python
# from sqlite_parser import tokenize_sql
# from sqlite_parser.debug import print_tokens
#
# tokens = tokenize_sql("SELECT id FROM users")
# print_tokens(tokens, highlight_pos=2)  # Highlight token at position 2
# ```
#
# ### AST Inspection
#
# ```python
# from sqlite_parser import parse_sql
# from sqlite_parser.debug import print_ast
#
# ast = parse_sql("SELECT * FROM users")
# print_ast(ast)  # Pretty-print entire AST tree
# ```
#
# ### Parser State Tracking
#
# ```python
# from sqlite_parser.debug import parser_debug_context
#
# with parser_debug_context(parser):
#     result = parser.parse()
#     state = parser.get_state()
#     print_state(state)
# ```

"""
Debug utilities for SQLite parser

Provides formatting and inspection tools for debugging the parser,
including token stream visualization, AST formatting, and parser tracing.
"""

from typing import List, Any
from contextlib import contextmanager
from .lexer import Token
from .ast_nodes import ASTNode
from .parser import Parser

#> ## Token Stream Formatter
#
# `format_token_stream()` creates a **tabular display** of all tokens with their types
# and values. This is crucial for understanding how the lexer tokenized the input.
#
# ### Features
#
# - **Indexed**: Each token shows its position in the stream
# - **Type Display**: Token type name (SELECT, IDENTIFIER, NUMBER, etc.)
# - **Value Display**: The actual text value
# - **Highlighting**: Optional `>>>` marker for a specific token position
#
# ### Output Example
#
# ```
# ======================================================================
# Token Stream
# ======================================================================
#    [  0] SELECT          'SELECT'
# >>> [  1] STAR            '*'
#    [  2] FROM            'FROM'
#    [  3] IDENTIFIER      'users'
# ======================================================================
# ```
#
# The highlighting helps visualize parser position during debugging.

def format_token_stream(tokens: List[Token], highlight_pos: int = None) -> str:
    """
    Format token stream for pretty printing

    Args:
        tokens: List of tokens to format
        highlight_pos: Optional position to highlight

    Returns:
        Formatted string representation
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Token Stream")
    lines.append("=" * 70)

    for i, token in enumerate(tokens):
        marker = ">>>" if i == highlight_pos else "   "
        type_str = f"{token.type.name:15}"
        value_str = f"{repr(token.value):20}"
        lines.append(f"{marker} [{i:3d}] {type_str} {value_str}")

    lines.append("=" * 70)
    return "\n".join(lines)

#> ## AST Tree Formatter
#
# `format_ast()` recursively formats **AST node trees** with proper indentation to show
# the hierarchical structure. This is essential for understanding what the parser built.
#
# ### Formatting Rules
#
# - **Nodes**: Show type name and attributes (excluding span for clarity)
# - **Lists**: Format as `[...]` with indented items
# - **Primitives**: Show with `repr()` for clarity (strings show quotes)
# - **None**: Displayed explicitly
# - **Nesting**: Each level indents 2 spaces
#
# ### Example Output
#
# ```
# SelectStatement(
#   select_core=
#     SelectCore(
#       columns=
#         [
#           ResultColumn(
#             expression=
#               Identifier(
#                 name='id'
#               )
#           )
#         ]
#       from_clause=
#         FromClause(
#           source=
#             TableReference(
#               name=QualifiedIdentifier(
#                 parts=['users']
#               )
#             )
#         )
#     )
# )
# ```
#
# This visualization makes it easy to verify the parser built the correct structure.

def format_ast(node: Any, indent: int = 0) -> str:
    """
    Format AST node tree for pretty printing

    Args:
        node: AST node to format
        indent: Current indentation level

    Returns:
        Formatted string representation
    """
    if node is None:
        return " " * indent + "None"

    if isinstance(node, list):
        if not node:
            return " " * indent + "[]"

        lines = [" " * indent + "["]
        for item in node:
            lines.append(format_ast(item, indent + 2))
        lines.append(" " * indent + "]")
        return "\n".join(lines)

    if not isinstance(node, ASTNode):
        return " " * indent + repr(node)

    # Format AST node
    node_type = type(node).__name__
    lines = [" " * indent + f"{node_type}("]

    # Get node attributes (excluding span)
    attrs = {}
    for key, value in node.__dict__.items():
        if key != 'span' and value is not None:
            attrs[key] = value

    for key, value in attrs.items():
        if isinstance(value, (list, ASTNode)):
            lines.append(" " * (indent + 2) + f"{key}=")
            lines.append(format_ast(value, indent + 4))
        else:
            lines.append(" " * (indent + 2) + f"{key}={repr(value)}")

    lines.append(" " * indent + ")")
    return "\n".join(lines)


def format_parser_trace(trace_log: List[str]) -> str:
    """
    Format parser trace log for pretty printing

    Args:
        trace_log: List of trace messages

    Returns:
        Formatted string representation
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Parser Trace")
    lines.append("=" * 70)
    lines.extend(trace_log)
    lines.append("=" * 70)
    return "\n".join(lines)


def format_parser_state(state: dict) -> str:
    """
    Format parser state dictionary for pretty printing

    Args:
        state: State dictionary from parser.get_state()

    Returns:
        Formatted string representation
    """
    lines = []
    lines.append("Parser State:")
    lines.append(f"  Position:      {state['pos']}")
    lines.append(f"  Current Token: {state['token_type']}:{repr(state['token_value'])}")
    lines.append(f"  Depth:         {state['depth']}")
    lines.append(f"  Active Method: {state['active_method']}")

    if state['stack']:
        lines.append(f"  Call Stack:")
        for i, method in enumerate(state['stack']):
            lines.append(f"    {i}. {method}")

    return "\n".join(lines)


@contextmanager
def parser_debug_context(parser: Parser, enable: bool = True):
    """
    Context manager for temporarily enabling parser debug mode

    Args:
        parser: Parser instance
        enable: Whether to enable debug mode

    Yields:
        Parser with debug enabled

    Example:
        with parser_debug_context(parser):
            result = parser.parse()
            parser.print_trace()
    """
    old_debug = parser.debug
    parser.debug = enable

    try:
        yield parser
    finally:
        parser.debug = old_debug


def print_tokens(tokens: List[Token], highlight_pos: int = None):
    """
    Print token stream to stdout

    Args:
        tokens: List of tokens
        highlight_pos: Optional position to highlight
    """
    print(format_token_stream(tokens, highlight_pos))


def print_ast(node: Any):
    """
    Print AST tree to stdout

    Args:
        node: AST node or list of nodes
    """
    print("=" * 70)
    print("AST")
    print("=" * 70)
    print(format_ast(node))
    print("=" * 70)


def print_state(state: dict):
    """
    Print parser state to stdout

    Args:
        state: State dictionary from parser.get_state()
    """
    print(format_parser_state(state))

#> ## One-Function Debugging
#
# `debug_parse()` is the **fastest way to debug** parser issues. It performs the complete
# parse workflow with optional verbose output showing every step.
#
# ### What It Does
#
# 1. **Lexes** the SQL into tokens
# 2. **Prints** token stream (if verbose)
# 3. **Parses** with debug tracing enabled
# 4. **Prints** parser trace log (if verbose)
# 5. **Prints** final AST (if verbose)
# 6. **Returns** parsed statements
#
# ### Usage
#
# ```python
# # Quick parse with no output
# statements = debug_parse("SELECT * FROM users")
#
# # Full debugging output
# statements = debug_parse("SELECT * FROM users", verbose=True)
# ```
#
# ### Verbose Output Includes
#
# - Token stream with indices and types
# - Parser trace showing method calls and token consumption
# - Final AST tree structure
#
# This is perfect for troubleshooting: paste in problematic SQL, set `verbose=True`,
# and see exactly what the parser is doing at each step.

def debug_parse(sql: str, verbose: bool = False) -> List[ASTNode]:
    """
    Parse SQL with debug tracing enabled

    Args:
        sql: SQL string to parse
        verbose: If True, print trace after parsing

    Returns:
        List of parsed statements

    Example:
        statements = debug_parse("SELECT * FROM users", verbose=True)
    """
    from .lexer import Lexer

    lexer = Lexer(sql)
    tokens = lexer.tokenize()

    if verbose:
        print_tokens(tokens)
        print()

    parser = Parser(tokens, debug=True)

    try:
        result = parser.parse()

        if verbose:
            print(format_parser_trace(parser.get_trace_log()))
            print()
            print_ast(result)

        return result

    except Exception as e:
        if verbose:
            print(format_parser_trace(parser.get_trace_log()))
            print()
            print(f"Error: {e}")
        raise


# Export main functions
__all__ = [
    'format_token_stream',
    'format_ast',
    'format_parser_trace',
    'format_parser_state',
    'parser_debug_context',
    'print_tokens',
    'print_ast',
    'print_state',
    'debug_parse',
]
