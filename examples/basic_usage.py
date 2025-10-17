#> # Basic Usage Examples
#
# This module demonstrates **practical usage patterns** for the sqlite-ast-parser library.
# It shows how to parse different SQL statement types and inspect the resulting AST nodes.
#
# ## What You'll Learn
#
# - How to call `parse_sql()` and interpret results
# - How to navigate AST node structures
# - How to handle parse errors gracefully
# - How to use `tokenize_sql()` for low-level analysis
#
# ## Examples Covered
#
# 1. **DML Statements**: SELECT, INSERT, UPDATE, DELETE
# 2. **DDL Statements**: CREATE TABLE with constraints
# 3. **Advanced Features**: CTEs (WITH clause), compound queries (UNION), window functions
# 4. **Transaction Control**: BEGIN, SAVEPOINT, COMMIT, ROLLBACK
# 5. **Error Handling**: How to catch and report parse errors
# 6. **Tokenization**: Low-level token inspection
#
# Each example function demonstrates a specific SQL feature and shows how to access
# the relevant parts of the AST.

"""
Basic Usage Examples for SQLite SQL Parser

Demonstrates how to use the parser for various SQL statements.
"""

import sys
sys.path.insert(0, '..')

from sqlite_parser import parse_sql, tokenize_sql
from sqlite_parser.errors import ParseError

#> ## SELECT Statement Parsing
#
# The SELECT statement is the most complex SQL statement type, supporting:
# - Column selection with expressions and aliases
# - Table joins (INNER, LEFT, RIGHT, CROSS, NATURAL)
# - WHERE clauses for filtering
# - GROUP BY and HAVING for aggregation
# - ORDER BY for sorting
# - LIMIT and OFFSET for pagination
#
# The parser returns a `SelectStatement` node with:
# - `select_core`: Contains columns, FROM, WHERE, GROUP BY
# - `order_by`: ORDER BY clause
# - `limit`: LIMIT expression
# - `offset`: OFFSET expression

def example_select():
    """Parse a SELECT statement"""
    print("=" * 60)
    print("SELECT Statement Example")
    print("=" * 60)

    sql = """
    SELECT u.id, u.name, COUNT(o.id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.age > 18
    GROUP BY u.id, u.name
    HAVING COUNT(o.id) > 0
    ORDER BY order_count DESC
    LIMIT 10
    """

    ast = parse_sql(sql)
    print(f"Parsed {len(ast)} statement(s)")
    print(f"\nStatement type: {type(ast[0]).__name__}")
    print(f"Has WHERE clause: {ast[0].select_core.where is not None}")
    print(f"Has GROUP BY: {ast[0].select_core.group_by is not None}")
    print(f"Has ORDER BY: {ast[0].order_by is not None}")
    print(f"Has LIMIT: {ast[0].limit is not None}")


def example_insert():
    """Parse an INSERT statement"""
    print("\n" + "=" * 60)
    print("INSERT Statement Example")
    print("=" * 60)

    sql = "INSERT INTO users (name, email, age) VALUES ('Alice', 'alice@example.com', 25)"

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Table: {stmt.table.parts}")
    print(f"Columns: {stmt.columns}")
    print(f"Number of rows: {len(stmt.values.rows) if stmt.values else 0}")


def example_update():
    """Parse an UPDATE statement"""
    print("\n" + "=" * 60)
    print("UPDATE Statement Example")
    print("=" * 60)

    sql = "UPDATE users SET age = age + 1, updated_at = CURRENT_TIMESTAMP WHERE id = 42"

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Table: {stmt.table.parts}")
    print(f"Number of assignments: {len(stmt.assignments)}")
    print(f"Has WHERE clause: {stmt.where is not None}")


def example_delete():
    """Parse a DELETE statement"""
    print("\n" + "=" * 60)
    print("DELETE Statement Example")
    print("=" * 60)

    sql = "DELETE FROM users WHERE created_at < date('now', '-1 year')"

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Table: {stmt.table.parts}")
    print(f"Has WHERE clause: {stmt.where is not None}")


def example_create_table():
    """Parse a CREATE TABLE statement"""
    print("\n" + "=" * 60)
    print("CREATE TABLE Statement Example")
    print("=" * 60)

    sql = """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL CHECK(price > 0),
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(name)
    )
    """

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Table: {stmt.table_name.parts}")
    print(f"IF NOT EXISTS: {stmt.if_not_exists}")
    print(f"Number of columns: {len(stmt.columns)}")
    print(f"Number of table constraints: {len(stmt.constraints)}")

    for col in stmt.columns:
        print(f"  Column: {col.name} {col.type_name or '(no type)'}")


#> ## Common Table Expressions (CTEs)
#
# WITH clauses (CTEs) allow **defining temporary named result sets** that can be referenced
# in the main query. They're especially powerful with the RECURSIVE keyword for hierarchical
# or iterative queries.
#
# ### Recursive CTE Pattern
#
# 1. **Anchor member**: Initial SELECT (e.g., `SELECT 1`)
# 2. **UNION ALL**: Combines anchor with recursive member
# 3. **Recursive member**: SELECT that references the CTE itself
# 4. **Termination**: WHERE clause stops recursion
#
# The AST provides:
# - `with_clause.recursive`: Boolean indicating if RECURSIVE keyword present
# - `with_clause.ctes`: List of CTE definitions
# - Each CTE has `name`, optional `columns`, and `select` query

def example_with_cte():
    """Parse a WITH clause (CTE)"""
    print("\n" + "=" * 60)
    print("WITH Clause (CTE) Example")
    print("=" * 60)

    sql = """
    WITH RECURSIVE cnt(x) AS (
        SELECT 1
        UNION ALL
        SELECT x+1 FROM cnt WHERE x < 10
    )
    SELECT x FROM cnt
    """

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Has WITH clause: {stmt.with_clause is not None}")
    print(f"Recursive: {stmt.with_clause.recursive}")
    print(f"Number of CTEs: {len(stmt.with_clause.ctes)}")


def example_compound_select():
    """Parse a compound SELECT with UNION"""
    print("\n" + "=" * 60)
    print("Compound SELECT (UNION) Example")
    print("=" * 60)

    sql = """
    SELECT name FROM employees
    UNION
    SELECT name FROM contractors
    ORDER BY name
    """

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Statement type: {type(stmt).__name__}")
    print(f"Number of compound parts: {len(stmt.compound_selects)}")
    if stmt.compound_selects:
        print(f"Compound operator: {stmt.compound_selects[0][0].value}")


def example_transactions():
    """Parse transaction control statements"""
    print("\n" + "=" * 60)
    print("Transaction Control Example")
    print("=" * 60)

    sqls = [
        "BEGIN TRANSACTION",
        "SAVEPOINT sp1",
        "UPDATE users SET balance = balance - 100 WHERE id = 1",
        "UPDATE users SET balance = balance + 100 WHERE id = 2",
        "RELEASE SAVEPOINT sp1",
        "COMMIT"
    ]

    for sql in sqls:
        ast = parse_sql(sql)
        print(f"{sql:60} -> {type(ast[0]).__name__}")


#> ## Error Handling
#
# The parser raises **typed exceptions** that provide detailed context about parsing failures.
# All parser errors inherit from `ParseError`, making them easy to catch.
#
# ### Error Information
#
# Parse errors include:
# - **Message**: Human-readable description of the problem
# - **Position**: Line and column numbers where the error occurred
# - **Context**: The problematic line with a caret (^) pointing to the error
#
# ### Best Practices
#
# - Catch `ParseError` for all parser failures
# - Display the error message to users (it includes context)
# - Use `try-except` when parsing user-provided SQL
# - Log errors for debugging and monitoring

def example_error_handling():
    """Demonstrate error handling"""
    print("\n" + "=" * 60)
    print("Error Handling Example")
    print("=" * 60)

    invalid_sql = "SELECT FROM"  # Missing column list

    try:
        ast = parse_sql(invalid_sql)
    except ParseError as e:
        print(f"Caught parse error:")
        print(f"  {e}")

#> ## Low-Level Tokenization
#
# The `tokenize_sql()` function provides **access to tokens without building an AST**.
# This is useful for:
# - Syntax highlighting
# - Building custom parsers
# - Debugging lexer issues
# - Token-based analysis (counting keywords, identifying patterns)
#
# Each token contains:
# - `type`: TokenType enum value (e.g., SELECT, IDENTIFIER, NUMBER)
# - `value`: The actual text (e.g., "SELECT", "users", "42")
# - `position`: Line and column where the token starts

def example_tokenization():
    """Show tokenization"""
    print("\n" + "=" * 60)
    print("Tokenization Example")
    print("=" * 60)

    sql = "SELECT * FROM users WHERE age > 18"

    tokens = tokenize_sql(sql)
    print(f"Tokenized into {len(tokens)} tokens:\n")

    for token in tokens[:10]:  # Show first 10 tokens
        print(f"  {token.type.name:20} {repr(token.value):20} at {token.position}")


def example_complex_query():
    """Parse a complex real-world query"""
    print("\n" + "=" * 60)
    print("Complex Query Example")
    print("=" * 60)

    sql = """
    WITH monthly_sales AS (
        SELECT
            strftime('%Y-%m', order_date) as month,
            product_id,
            SUM(quantity) as total_quantity,
            SUM(price * quantity) as total_revenue
        FROM orders
        WHERE order_date >= date('now', '-12 months')
        GROUP BY month, product_id
    )
    SELECT
        p.name as product_name,
        ms.month,
        ms.total_quantity,
        ms.total_revenue,
        ROUND(ms.total_revenue / ms.total_quantity, 2) as avg_price,
        LAG(ms.total_revenue) OVER (
            PARTITION BY ms.product_id
            ORDER BY ms.month
        ) as prev_month_revenue
    FROM monthly_sales ms
    JOIN products p ON ms.product_id = p.id
    WHERE ms.total_quantity > 10
    ORDER BY ms.month DESC, ms.total_revenue DESC
    LIMIT 100
    """

    ast = parse_sql(sql)
    stmt = ast[0]

    print(f"Successfully parsed complex query!")
    print(f"  Has CTE: {stmt.with_clause is not None}")
    print(f"  Number of result columns: {len(stmt.select_core.columns)}")
    print(f"  Has window functions: (check for OVER clauses)")
    print(f"  Has joins: (check FROM clause)")


def main():
    """Run all examples"""
    print("\n" + "#" * 60)
    print("# SQLite SQL Parser - Usage Examples")
    print("#" * 60)

    example_select()
    example_insert()
    example_update()
    example_delete()
    example_create_table()
    example_with_cte()
    example_compound_select()
    example_transactions()
    example_complex_query()
    example_tokenization()
    example_error_handling()

    print("\n" + "#" * 60)
    print("# All examples completed successfully!")
    print("#" * 60)


if __name__ == "__main__":
    main()
