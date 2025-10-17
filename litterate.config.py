#> # Litterate Configuration for sqlite-ast-parser
#
# This configuration file defines how litterate should process the
# sqlite-ast-parser codebase to generate literate programming documentation.

name = "sqlite-ast-parser"

description = """
A **complete, production-ready SQLite SQL parser** in Python that returns
detailed Abstract Syntax Trees (AST) for all SQLite SQL statements.

This literate programming documentation provides comprehensive explanations of
the parser's architecture, implementation details, and usage patterns.
"""

# Files to process - include annotated core package files and examples
# Ordered to present concepts from foundation to implementation
files = [
    "./sqlite_parser/__init__.py",         # Public API overview
    "./sqlite_parser/utils.py",            # Token types, keywords, precedence
    "./sqlite_parser/errors.py",           # Error handling
    "./sqlite_parser/ast_nodes.py",        # AST node definitions
    "./sqlite_parser/debug.py",            # Debugging utilities
    "./examples/basic_usage.py",           # Usage examples
]

# Output directory for generated HTML documentation
output_directory = "./literate_docs/"

# Base URL for the documentation (use ./ for local viewing)
baseURL = "./"

# Python annotation markers
annotation_start_mark = "#>"
annotation_continue_mark = "#"

# Line wrapping (0 = no wrapping)
wrap = 0
