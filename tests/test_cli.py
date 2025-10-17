#!/usr/bin/env python3
"""
Test CLI for SQLite Parser

Interactive test runner with targeted execution, verbose modes, and debugging.
Inspired by demo-based testing approach.

Usage:
    python tests/test_cli.py all              # Run all tests
    python tests/test_cli.py select           # Run SELECT tests only
    python tests/test_cli.py "Basic SELECT"   # Run specific test
    python tests/test_cli.py --pattern TRIGGER # Run tests matching pattern
    python tests/test_cli.py all -v           # Verbose: show SQL and AST
    python tests/test_cli.py all -vv          # Very verbose: show parser trace
    python tests/test_cli.py all -vvv         # Extra verbose: tokens + trace
    python tests/test_cli.py repl             # Interactive REPL mode
"""

import sys
import os
import re
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlite_parser import parse_sql, tokenize_sql
from sqlite_parser.parser import Parser
from sqlite_parser.ast_nodes import *
from sqlite_parser.errors import ParseError
from sqlite_parser.debug import (
    print_tokens, print_ast, format_parser_trace,
    format_parser_state, debug_parse
)


# ============================================================================
# Test Infrastructure
# ============================================================================

class TestRunner:
    """Manages test execution with verbose output and filtering"""

    def __init__(self, verbose: int = 0):
        """
        Initialize test runner

        Args:
            verbose: Verbosity level (0-3)
                0: Minimal output (pass/fail only)
                1: Show SQL and AST details
                2: Show parser debug trace
                3: Show tokens + parser trace
        """
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.step_number = 1

    def header(self, title: str):
        """Print section header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def step(self, description: str):
        """Print step with number"""
        print(f"\n[Step {self.step_number}] {description}")
        self.step_number += 1

    def test(self, name: str, sql: str, expected_type=None) -> bool:
        """
        Run a single test

        Args:
            name: Test name
            sql: SQL to parse
            expected_type: Expected AST node type

        Returns:
            True if test passed, False otherwise
        """
        try:
            # Show test info
            if self.verbose >= 1:
                print(f"\nTest: {name}")
                print(f"SQL: {sql[:100]}{'...' if len(sql) > 100 else ''}")

            # Tokenize if very verbose
            if self.verbose >= 3:
                print("\nTokens:")
                tokens = tokenize_sql(sql)
                print_tokens(tokens)

            # Parse with debug if requested
            if self.verbose >= 2:
                print("\nParsing with debug trace...")
                from sqlite_parser.lexer import Lexer
                lexer = Lexer(sql)
                tokens = lexer.tokenize()
                parser = Parser(tokens, debug=True)
                ast = parser.parse()

                print("\nParser Trace:")
                print(format_parser_trace(parser.get_trace_log()))
            else:
                ast = parse_sql(sql)

            # Validate result
            if not ast:
                raise Exception("No statements parsed")

            if expected_type and not isinstance(ast[0], expected_type):
                raise Exception(
                    f"Expected {expected_type.__name__}, got {type(ast[0]).__name__}"
                )

            # Show AST if verbose
            if self.verbose >= 1:
                print("\nAST:")
                print_ast(ast)

            # Mark success
            self.passed += 1
            print(f"  ✓ {name}")
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append((name, sql, str(e)))
            print(f"  ✗ {name}: {e}")

            if self.verbose >= 1:
                import traceback
                traceback.print_exc()

            return False

    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"Test Results: {self.passed}/{total} passed ({self.passed * 100 // total if total > 0 else 0}%)")

        if self.failed > 0:
            print(f"\n{self.failed} FAILED:")
            for name, sql, error in self.errors:
                print(f"\n  {name}")
                print(f"    SQL: {sql[:100]}...")
                print(f"    Error: {error}")

        print("=" * 70)

        return self.failed == 0


# ============================================================================
# Test Suites (imported from test_all_statements.py structure)
# ============================================================================

def test_select_statements(runner: TestRunner):
    """Test SELECT statements"""
    runner.header("Testing SELECT Statements")

    # Basic SELECT
    runner.test("Basic SELECT", "SELECT * FROM users", SelectStatement)

    # SELECT with columns
    runner.test("SELECT columns", "SELECT id, name, email FROM users", SelectStatement)

    # SELECT with WHERE
    runner.test("SELECT WHERE", "SELECT * FROM users WHERE age > 18", SelectStatement)

    # SELECT with JOIN
    runner.test(
        "SELECT JOIN",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
        SelectStatement
    )

    # SELECT with GROUP BY
    runner.test(
        "SELECT GROUP BY",
        "SELECT country, COUNT(*) FROM users GROUP BY country",
        SelectStatement
    )

    # SELECT with ORDER BY
    runner.test(
        "SELECT ORDER BY",
        "SELECT * FROM users ORDER BY created_at DESC",
        SelectStatement
    )

    # SELECT with LIMIT
    runner.test(
        "SELECT LIMIT",
        "SELECT * FROM users LIMIT 10 OFFSET 20",
        SelectStatement
    )


def test_create_trigger_statements(runner: TestRunner):
    """Test CREATE TRIGGER statements"""
    runner.header("Testing CREATE TRIGGER Statements")

    # BEFORE INSERT trigger
    runner.test(
        "CREATE TRIGGER BEFORE INSERT",
        """CREATE TRIGGER validate_user BEFORE INSERT ON users
           BEGIN
               SELECT RAISE(ABORT, 'Invalid email') WHERE NEW.email NOT LIKE '%@%';
           END""",
        CreateTriggerStatement
    )

    # AFTER UPDATE trigger
    runner.test(
        "CREATE TRIGGER AFTER UPDATE",
        """CREATE TRIGGER update_modified AFTER UPDATE ON users
           BEGIN
               UPDATE users SET modified_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
           END""",
        CreateTriggerStatement
    )


def test_pragma_statements(runner: TestRunner):
    """Test PRAGMA statements"""
    runner.header("Testing PRAGMA Statements")

    # PRAGMA query
    runner.test("PRAGMA", "PRAGMA table_info(users)", PragmaStatement)

    # PRAGMA assignment
    runner.test("PRAGMA assignment", "PRAGMA foreign_keys = ON", PragmaStatement)


def test_window_functions(runner: TestRunner):
    """Test window functions"""
    runner.header("Testing Window Functions")

    # ROWS frame
    runner.test(
        "ROWS frame",
        "SELECT SUM(amount) OVER (ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM transactions",
        SelectStatement
    )

    # RANGE frame
    runner.test(
        "RANGE frame",
        "SELECT AVG(price) OVER (ORDER BY date RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM prices",
        SelectStatement
    )


def test_expressions(runner: TestRunner):
    """Test various expressions"""
    runner.header("Testing Expressions")

    # IN with list
    runner.test(
        "IN list",
        "SELECT * FROM users WHERE country IN ('US', 'UK', 'CA')",
        SelectStatement
    )

    # IN with subquery
    runner.test(
        "IN subquery",
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
        SelectStatement
    )


# ============================================================================
# Test Categories
# ============================================================================

TEST_CATEGORIES = {
    'select': test_select_statements,
    'trigger': test_create_trigger_statements,
    'pragma': test_pragma_statements,
    'window': test_window_functions,
    'expressions': test_expressions,
}


# ============================================================================
# REPL Mode
# ============================================================================

def run_repl(verbose: int = 0):
    """
    Interactive REPL mode for testing SQL interactively

    Args:
        verbose: Verbosity level
    """
    print("=" * 70)
    print("SQLite Parser - Interactive REPL")
    print("=" * 70)
    print("Enter SQL to parse (or 'quit' to exit)")
    print("Commands:")
    print("  :tokens  - Show token stream for last input")
    print("  :ast     - Show AST for last input")
    print("  :trace   - Show parser trace for last input")
    print("  :verbose N - Set verbosity level (0-3)")
    print("=" * 70)

    last_sql = None
    last_result = None
    last_tokens = None
    last_parser = None

    while True:
        try:
            line = input("\nsql> ").strip()

            if not line:
                continue

            if line.lower() in ('quit', 'exit', ':q'):
                print("Goodbye!")
                break

            # Handle commands
            if line.startswith(':'):
                cmd = line[1:].lower().strip()

                if cmd == 'tokens' and last_tokens:
                    print_tokens(last_tokens)

                elif cmd == 'ast' and last_result:
                    print_ast(last_result)

                elif cmd == 'trace' and last_parser:
                    print(format_parser_trace(last_parser.get_trace_log()))

                elif cmd.startswith('verbose'):
                    parts = cmd.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        verbose = int(parts[1])
                        print(f"Verbosity set to {verbose}")
                    else:
                        print("Usage: :verbose N (where N is 0-3)")

                else:
                    print(f"Unknown command: {line}")

                continue

            # Parse SQL
            last_sql = line

            from sqlite_parser.lexer import Lexer
            lexer = Lexer(line)
            last_tokens = lexer.tokenize()

            last_parser = Parser(last_tokens, debug=(verbose >= 2))
            last_result = last_parser.parse()

            # Show results based on verbosity
            if verbose >= 3:
                print("\nTokens:")
                print_tokens(last_tokens)

            if verbose >= 2:
                print("\nParser Trace:")
                print(format_parser_trace(last_parser.get_trace_log()))

            if verbose >= 1:
                print("\nAST:")
                print_ast(last_result)

            print(f"\n✓ Parsed {len(last_result)} statement(s)")
            for i, stmt in enumerate(last_result):
                print(f"  [{i}] {type(stmt).__name__}")

        except KeyboardInterrupt:
            print("\nUse 'quit' or Ctrl+D to exit")

        except EOFError:
            print("\nGoodbye!")
            break

        except Exception as e:
            print(f"\n✗ Error: {e}")

            if verbose >= 1:
                import traceback
                traceback.print_exc()

            if last_parser and verbose >= 2:
                print("\nParser Trace:")
                print(format_parser_trace(last_parser.get_trace_log()))


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for test CLI"""
    import argparse

    parser = argparse.ArgumentParser(
        description="SQLite Parser Test CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'target',
        nargs='?',
        default='all',
        help='Test target: all, <category>, <test-name>, or repl'
    )

    parser.add_argument(
        '--pattern', '-p',
        help='Run tests matching this pattern'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (use -v, -vv, or -vvv)'
    )

    args = parser.parse_args()

    # REPL mode
    if args.target == 'repl':
        run_repl(verbose=args.verbose)
        return 0

    # Create test runner
    runner = TestRunner(verbose=args.verbose)

    # Run tests
    if args.target == 'all':
        # Run all categories
        for category_name, category_func in TEST_CATEGORIES.items():
            category_func(runner)

    elif args.target in TEST_CATEGORIES:
        # Run specific category
        TEST_CATEGORIES[args.target](runner)

    elif args.pattern:
        # Run tests matching pattern
        print(f"Running tests matching pattern: {args.pattern}")
        pattern = re.compile(args.pattern, re.IGNORECASE)

        for category_name, category_func in TEST_CATEGORIES.items():
            if pattern.search(category_name):
                category_func(runner)

    else:
        print(f"Unknown target: {args.target}")
        print("Available targets: all, repl, " + ", ".join(TEST_CATEGORIES.keys()))
        return 1

    # Show summary
    runner.summary()

    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
