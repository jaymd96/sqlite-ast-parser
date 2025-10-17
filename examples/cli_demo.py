#!/usr/bin/env python3
"""
Interactive CLI Demo for SQLite SQL Parser

Allows you to test the parser interactively by entering SQL statements.
"""

import sys
sys.path.insert(0, '..')

from sqlite_parser import parse_sql, tokenize_sql
from sqlite_parser.errors import ParseError
import json


def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("SQLite SQL Parser - Interactive Demo")
    print("=" * 70)
    print("Enter SQL statements to parse them.")
    print("Commands:")
    print("  .tokens  - Show tokenization for next SQL")
    print("  .ast     - Show AST for next SQL (default)")
    print("  .json    - Show AST as JSON for next SQL")
    print("  .help    - Show this help")
    print("  .examples - Show example SQL statements")
    print("  .quit    - Exit")
    print("=" * 70)
    print()


def print_examples():
    """Print example SQL statements"""
    examples = [
        ("Simple SELECT", "SELECT * FROM users WHERE age > 18;"),
        ("JOIN", "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id;"),
        ("CTE", "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x < 10) SELECT * FROM cnt;"),
        ("INSERT", "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');"),
        ("UPDATE", "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = 42;"),
        ("DELETE", "DELETE FROM sessions WHERE expired_at < datetime('now');"),
        ("CREATE TABLE", "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL CHECK(price > 0));"),
        ("UPSERT", "INSERT INTO stats (key, value) VALUES ('counter', 1) ON CONFLICT(key) DO UPDATE SET value = value + 1;"),
        ("Window Function", "SELECT name, salary, AVG(salary) OVER (PARTITION BY department) FROM employees;"),
        ("Transaction", "BEGIN TRANSACTION; UPDATE accounts SET balance = balance - 100 WHERE id = 1; COMMIT;"),
    ]

    print("\n" + "=" * 70)
    print("Example SQL Statements")
    print("=" * 70)
    for title, sql in examples:
        print(f"\n{title}:")
        print(f"  {sql}")
    print("=" * 70 + "\n")


def print_ast(ast, indent=0):
    """Pretty print AST"""
    from enum import Enum

    prefix = "  " * indent

    if isinstance(ast, list):
        for item in ast:
            print_ast(item, indent)
    elif isinstance(ast, Enum):
        # Print enum name only
        print(f"{prefix}{ast.__class__.__name__}.{ast.name}")
    elif hasattr(ast, '__dict__'):
        class_name = ast.__class__.__name__
        print(f"{prefix}{class_name}(")

        for key, value in ast.__dict__.items():
            if key == 'span':  # Skip span for readability
                continue

            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                print(f"{prefix}  {key}={repr(value)}")
            elif isinstance(value, Enum):
                print(f"{prefix}  {key}={value.__class__.__name__}.{value.name}")
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                print(f"{prefix}  {key}=[")
                for item in value:
                    print_ast(item, indent + 2)
                print(f"{prefix}  ]")
            elif hasattr(value, '__dict__'):
                print(f"{prefix}  {key}=")
                print_ast(value, indent + 2)
            else:
                print(f"{prefix}  {key}={value}")

        print(f"{prefix})")
    else:
        print(f"{prefix}{repr(ast)}")


def ast_to_dict(obj):
    """Convert AST to dictionary for JSON serialization"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, list):
        return [ast_to_dict(item) for item in obj]
    elif isinstance(obj, tuple):
        return [ast_to_dict(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        result = {'_type': obj.__class__.__name__}
        for key, value in obj.__dict__.items():
            if key == 'span':  # Skip span for JSON output
                continue
            if value is not None:
                result[key] = ast_to_dict(value)
        return result
    elif hasattr(obj, 'value'):  # Enum
        return obj.value
    else:
        return str(obj)


def run_interactive():
    """Run interactive REPL"""
    print_banner()

    mode = 'ast'  # Default mode

    while True:
        try:
            # Get input
            line = input("sql> ")

            if not line.strip():
                continue

            # Handle commands
            if line.startswith('.'):
                cmd = line.strip().lower()
                if cmd == '.quit' or cmd == '.exit':
                    print("Goodbye!")
                    break
                elif cmd == '.help':
                    print_banner()
                elif cmd == '.examples':
                    print_examples()
                elif cmd == '.tokens':
                    mode = 'tokens'
                    print("Mode: Show tokens")
                elif cmd == '.ast':
                    mode = 'ast'
                    print("Mode: Show AST")
                elif cmd == '.json':
                    mode = 'json'
                    print("Mode: Show JSON")
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type .help for help")
                continue

            # Parse SQL
            sql = line

            # Handle multi-line input
            if not sql.rstrip().endswith(';'):
                while True:
                    try:
                        next_line = input("...> ")
                        sql += "\n" + next_line
                        if next_line.rstrip().endswith(';'):
                            break
                    except EOFError:
                        break

            # Process based on mode
            try:
                if mode == 'tokens':
                    # Tokenize
                    tokens = tokenize_sql(sql)
                    print(f"\n{len(tokens)} tokens:")
                    print("-" * 70)
                    for i, token in enumerate(tokens):
                        print(f"  [{i:3d}] {token.type.name:20} {repr(token.value):30} @ {token.position}")
                    print("-" * 70 + "\n")

                else:
                    # Parse
                    ast = parse_sql(sql)

                    if not ast:
                        print("No statements parsed\n")
                        continue

                    print(f"\n{len(ast)} statement(s) parsed:")
                    print("-" * 70)

                    if mode == 'json':
                        # JSON output
                        ast_dict = [ast_to_dict(stmt) for stmt in ast]
                        print(json.dumps(ast_dict, indent=2))
                    else:
                        # Pretty print AST
                        for stmt in ast:
                            print_ast(stmt)

                    print("-" * 70 + "\n")

            except ParseError as e:
                print(f"\n{e}\n")

        except EOFError:
            print("\nGoodbye!")
            break

        except KeyboardInterrupt:
            print("\nInterrupted. Type .quit to exit.\n")

        except Exception as e:
            print(f"Error: {e}\n")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python cli_demo.py")
        print("\nInteractive SQL parser demo.")
        print("Type SQL statements and see the AST.")
        return

    run_interactive()


if __name__ == "__main__":
    main()
