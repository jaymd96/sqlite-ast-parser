"""
Comprehensive Test Suite for SQLite Parser

Tests ALL statement types from the SQLite syntax reference.
"""

import sys
sys.path.insert(0, '..')

from sqlite_parser import parse_sql
from sqlite_parser.ast_nodes import *
from sqlite_parser.errors import ParseError


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(self, name, sql, expected_type=None):
        """Run a single test"""
        try:
            ast = parse_sql(sql)
            if not ast:
                raise Exception("No statements parsed")

            if expected_type and not isinstance(ast[0], expected_type):
                raise Exception(f"Expected {expected_type.__name__}, got {type(ast[0]).__name__}")

            self.passed += 1
            print(f"  ✓ {name}")
            return ast
        except Exception as e:
            self.failed += 1
            self.errors.append((name, sql, str(e)))
            print(f"  ✗ {name}: {e}")
            return None

    def summary(self):
        """Print summary"""
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\n{self.failed} FAILED:")
            for name, sql, error in self.errors:
                print(f"\n  {name}")
                print(f"    SQL: {sql[:100]}...")
                print(f"    Error: {error}")
        print("=" * 70)


def test_select_statements(results):
    """Test SELECT statements"""
    print("\n" + "=" * 70)
    print("Testing SELECT Statements")
    print("=" * 70)

    # Basic SELECT
    results.test("Basic SELECT", "SELECT * FROM users", SelectStatement)

    # SELECT with columns
    results.test("SELECT columns", "SELECT id, name, email FROM users", SelectStatement)

    # SELECT with WHERE
    results.test("SELECT WHERE", "SELECT * FROM users WHERE age > 18", SelectStatement)

    # SELECT with JOIN
    results.test("SELECT JOIN",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
        SelectStatement)

    # SELECT with LEFT JOIN
    results.test("SELECT LEFT JOIN",
        "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id",
        SelectStatement)

    # SELECT with GROUP BY
    results.test("SELECT GROUP BY",
        "SELECT country, COUNT(*) FROM users GROUP BY country",
        SelectStatement)

    # SELECT with HAVING
    results.test("SELECT HAVING",
        "SELECT country, COUNT(*) as cnt FROM users GROUP BY country HAVING cnt > 10",
        SelectStatement)

    # SELECT with ORDER BY
    results.test("SELECT ORDER BY",
        "SELECT * FROM users ORDER BY created_at DESC",
        SelectStatement)

    # SELECT with LIMIT
    results.test("SELECT LIMIT",
        "SELECT * FROM users LIMIT 10 OFFSET 20",
        SelectStatement)

    # SELECT DISTINCT
    results.test("SELECT DISTINCT",
        "SELECT DISTINCT country FROM users",
        SelectStatement)

    # SELECT with subquery
    results.test("SELECT subquery",
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
        SelectStatement)

    # SELECT with UNION
    results.test("SELECT UNION",
        "SELECT name FROM users UNION SELECT name FROM customers",
        SelectStatement)

    # SELECT with INTERSECT
    results.test("SELECT INTERSECT",
        "SELECT email FROM users INTERSECT SELECT email FROM subscribers",
        SelectStatement)

    # SELECT with EXCEPT
    results.test("SELECT EXCEPT",
        "SELECT email FROM users EXCEPT SELECT email FROM unsubscribed",
        SelectStatement)


def test_cte_statements(results):
    """Test WITH (CTE) statements"""
    print("\n" + "=" * 70)
    print("Testing WITH (CTE) Statements")
    print("=" * 70)

    # Simple CTE
    results.test("Simple CTE",
        "WITH tmp AS (SELECT * FROM users) SELECT * FROM tmp",
        SelectStatement)

    # Multiple CTEs
    results.test("Multiple CTEs",
        "WITH t1 AS (SELECT * FROM users), t2 AS (SELECT * FROM orders) SELECT * FROM t1, t2",
        SelectStatement)

    # Recursive CTE
    results.test("Recursive CTE",
        """WITH RECURSIVE cnt(x) AS (
            SELECT 1
            UNION ALL
            SELECT x+1 FROM cnt WHERE x < 10
        )
        SELECT x FROM cnt""",
        SelectStatement)


def test_insert_statements(results):
    """Test INSERT statements"""
    print("\n" + "=" * 70)
    print("Testing INSERT Statements")
    print("=" * 70)

    # Basic INSERT
    results.test("Basic INSERT",
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')",
        InsertStatement)

    # INSERT multiple rows
    results.test("INSERT multiple rows",
        "INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie')",
        InsertStatement)

    # INSERT with SELECT
    results.test("INSERT SELECT",
        "INSERT INTO archive SELECT * FROM users WHERE created_at < '2020-01-01'",
        InsertStatement)

    # INSERT DEFAULT VALUES
    results.test("INSERT DEFAULT VALUES",
        "INSERT INTO users DEFAULT VALUES",
        InsertStatement)

    # INSERT OR REPLACE
    results.test("INSERT OR REPLACE",
        "INSERT OR REPLACE INTO users (id, name) VALUES (1, 'Alice')",
        InsertStatement)

    # INSERT OR IGNORE
    results.test("INSERT OR IGNORE",
        "INSERT OR IGNORE INTO users (id, name) VALUES (1, 'Alice')",
        InsertStatement)

    # REPLACE
    results.test("REPLACE",
        "REPLACE INTO users (id, name) VALUES (1, 'Alice')",
        InsertStatement)

    # INSERT with UPSERT
    results.test("INSERT UPSERT",
        """INSERT INTO users (id, name, count) VALUES (1, 'Alice', 1)
           ON CONFLICT(id) DO UPDATE SET count = count + 1""",
        InsertStatement)

    # INSERT with RETURNING
    results.test("INSERT RETURNING",
        "INSERT INTO users (name) VALUES ('Alice') RETURNING id, name",
        InsertStatement)


def test_update_statements(results):
    """Test UPDATE statements"""
    print("\n" + "=" * 70)
    print("Testing UPDATE Statements")
    print("=" * 70)

    # Basic UPDATE
    results.test("Basic UPDATE",
        "UPDATE users SET name = 'Alice' WHERE id = 1",
        UpdateStatement)

    # UPDATE multiple columns
    results.test("UPDATE multiple columns",
        "UPDATE users SET name = 'Alice', email = 'alice@example.com' WHERE id = 1",
        UpdateStatement)

    # UPDATE with expression
    results.test("UPDATE expression",
        "UPDATE users SET age = age + 1 WHERE id = 1",
        UpdateStatement)

    # UPDATE OR IGNORE
    results.test("UPDATE OR IGNORE",
        "UPDATE OR IGNORE users SET email = 'new@example.com' WHERE id = 1",
        UpdateStatement)

    # UPDATE with FROM (extension)
    results.test("UPDATE FROM",
        "UPDATE inventory SET quantity = quantity - o.qty FROM orders o WHERE inventory.product_id = o.product_id",
        UpdateStatement)

    # UPDATE with RETURNING
    results.test("UPDATE RETURNING",
        "UPDATE users SET age = age + 1 WHERE id = 1 RETURNING *",
        UpdateStatement)


def test_delete_statements(results):
    """Test DELETE statements"""
    print("\n" + "=" * 70)
    print("Testing DELETE Statements")
    print("=" * 70)

    # Basic DELETE
    results.test("Basic DELETE",
        "DELETE FROM users WHERE id = 1",
        DeleteStatement)

    # DELETE all rows
    results.test("DELETE all",
        "DELETE FROM users",
        DeleteStatement)

    # DELETE with complex WHERE
    results.test("DELETE complex WHERE",
        "DELETE FROM users WHERE created_at < date('now', '-1 year') AND status = 'inactive'",
        DeleteStatement)

    # DELETE with RETURNING
    results.test("DELETE RETURNING",
        "DELETE FROM users WHERE id = 1 RETURNING *",
        DeleteStatement)


def test_create_table_statements(results):
    """Test CREATE TABLE statements"""
    print("\n" + "=" * 70)
    print("Testing CREATE TABLE Statements")
    print("=" * 70)

    # Basic CREATE TABLE
    results.test("Basic CREATE TABLE",
        "CREATE TABLE users (id INTEGER, name TEXT)",
        CreateTableStatement)

    # CREATE TABLE IF NOT EXISTS
    results.test("CREATE TABLE IF NOT EXISTS",
        "CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT)",
        CreateTableStatement)

    # CREATE TABLE with PRIMARY KEY
    results.test("CREATE TABLE PRIMARY KEY",
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
        CreateTableStatement)

    # CREATE TABLE with AUTOINCREMENT
    results.test("CREATE TABLE AUTOINCREMENT",
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)",
        CreateTableStatement)

    # CREATE TABLE with NOT NULL
    results.test("CREATE TABLE NOT NULL",
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
        CreateTableStatement)

    # CREATE TABLE with UNIQUE
    results.test("CREATE TABLE UNIQUE",
        "CREATE TABLE users (id INTEGER, email TEXT UNIQUE)",
        CreateTableStatement)

    # CREATE TABLE with CHECK
    results.test("CREATE TABLE CHECK",
        "CREATE TABLE users (id INTEGER, age INTEGER CHECK(age >= 0))",
        CreateTableStatement)

    # CREATE TABLE with DEFAULT
    results.test("CREATE TABLE DEFAULT",
        "CREATE TABLE users (id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)",
        CreateTableStatement)

    # CREATE TABLE with FOREIGN KEY
    results.test("CREATE TABLE FOREIGN KEY",
        "CREATE TABLE orders (id INTEGER, user_id INTEGER REFERENCES users(id))",
        CreateTableStatement)

    # CREATE TABLE with table constraints
    results.test("CREATE TABLE table constraints",
        """CREATE TABLE users (
            id INTEGER,
            email TEXT,
            PRIMARY KEY(id),
            UNIQUE(email)
        )""",
        CreateTableStatement)

    # CREATE TABLE with composite PRIMARY KEY
    results.test("CREATE TABLE composite PRIMARY KEY",
        "CREATE TABLE user_roles (user_id INTEGER, role_id INTEGER, PRIMARY KEY(user_id, role_id))",
        CreateTableStatement)

    # CREATE TABLE WITHOUT ROWID
    results.test("CREATE TABLE WITHOUT ROWID",
        "CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT) WITHOUT ROWID",
        CreateTableStatement)

    # CREATE TABLE STRICT
    results.test("CREATE TABLE STRICT",
        "CREATE TABLE users (id INTEGER, name TEXT) STRICT",
        CreateTableStatement)

    # CREATE TABLE AS SELECT
    results.test("CREATE TABLE AS SELECT",
        "CREATE TABLE archive AS SELECT * FROM users WHERE created_at < '2020-01-01'",
        CreateTableStatement)

    # CREATE TEMPORARY TABLE
    results.test("CREATE TEMP TABLE",
        "CREATE TEMP TABLE session_data (key TEXT, value TEXT)",
        CreateTableStatement)


def test_alter_table_statements(results):
    """Test ALTER TABLE statements"""
    print("\n" + "=" * 70)
    print("Testing ALTER TABLE Statements")
    print("=" * 70)

    # ALTER TABLE RENAME TO
    results.test("ALTER TABLE RENAME TO",
        "ALTER TABLE users RENAME TO customers",
        AlterTableStatement)

    # ALTER TABLE RENAME COLUMN
    results.test("ALTER TABLE RENAME COLUMN",
        "ALTER TABLE users RENAME COLUMN name TO full_name",
        AlterTableStatement)

    # ALTER TABLE ADD COLUMN
    results.test("ALTER TABLE ADD COLUMN",
        "ALTER TABLE users ADD COLUMN phone TEXT",
        AlterTableStatement)

    # ALTER TABLE DROP COLUMN
    results.test("ALTER TABLE DROP COLUMN",
        "ALTER TABLE users DROP COLUMN phone",
        AlterTableStatement)


def test_create_index_statements(results):
    """Test CREATE INDEX statements"""
    print("\n" + "=" * 70)
    print("Testing CREATE INDEX Statements")
    print("=" * 70)

    # Basic CREATE INDEX
    results.test("Basic CREATE INDEX",
        "CREATE INDEX idx_users_email ON users(email)",
        CreateIndexStatement)

    # CREATE UNIQUE INDEX
    results.test("CREATE UNIQUE INDEX",
        "CREATE UNIQUE INDEX idx_users_email ON users(email)",
        CreateIndexStatement)

    # CREATE INDEX IF NOT EXISTS
    results.test("CREATE INDEX IF NOT EXISTS",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        CreateIndexStatement)

    # CREATE INDEX on multiple columns
    results.test("CREATE INDEX multiple columns",
        "CREATE INDEX idx_users_name_email ON users(name, email)",
        CreateIndexStatement)

    # CREATE INDEX with WHERE (partial index)
    results.test("CREATE INDEX partial",
        "CREATE INDEX idx_active_users ON users(email) WHERE status = 'active'",
        CreateIndexStatement)

    # CREATE INDEX with expression
    results.test("CREATE INDEX expression",
        "CREATE INDEX idx_users_lower_email ON users(lower(email))",
        CreateIndexStatement)


def test_create_view_statements(results):
    """Test CREATE VIEW statements"""
    print("\n" + "=" * 70)
    print("Testing CREATE VIEW Statements")
    print("=" * 70)

    # Basic CREATE VIEW
    results.test("Basic CREATE VIEW",
        "CREATE VIEW active_users AS SELECT * FROM users WHERE status = 'active'",
        CreateViewStatement)

    # CREATE VIEW IF NOT EXISTS
    results.test("CREATE VIEW IF NOT EXISTS",
        "CREATE VIEW IF NOT EXISTS active_users AS SELECT * FROM users WHERE status = 'active'",
        CreateViewStatement)

    # CREATE VIEW with column list
    results.test("CREATE VIEW with columns",
        "CREATE VIEW user_emails(id, email) AS SELECT id, email FROM users",
        CreateViewStatement)

    # CREATE TEMP VIEW
    results.test("CREATE TEMP VIEW",
        "CREATE TEMP VIEW session_users AS SELECT * FROM users WHERE session_id = 123",
        CreateViewStatement)


def test_create_trigger_statements(results):
    """Test CREATE TRIGGER statements"""
    print("\n" + "=" * 70)
    print("Testing CREATE TRIGGER Statements")
    print("=" * 70)

    # BEFORE INSERT trigger
    results.test("CREATE TRIGGER BEFORE INSERT",
        """CREATE TRIGGER validate_user BEFORE INSERT ON users
           BEGIN
               SELECT RAISE(ABORT, 'Invalid email') WHERE NEW.email NOT LIKE '%@%';
           END""",
        CreateTriggerStatement)

    # AFTER UPDATE trigger
    results.test("CREATE TRIGGER AFTER UPDATE",
        """CREATE TRIGGER update_modified AFTER UPDATE ON users
           BEGIN
               UPDATE users SET modified_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
           END""",
        CreateTriggerStatement)

    # AFTER DELETE trigger
    results.test("CREATE TRIGGER AFTER DELETE",
        """CREATE TRIGGER archive_user AFTER DELETE ON users
           BEGIN
               INSERT INTO users_archive SELECT * FROM users WHERE id = OLD.id;
           END""",
        CreateTriggerStatement)

    # UPDATE OF trigger
    results.test("CREATE TRIGGER UPDATE OF",
        """CREATE TRIGGER update_email AFTER UPDATE OF email ON users
           BEGIN
               UPDATE users SET email_verified = 0 WHERE id = NEW.id;
           END""",
        CreateTriggerStatement)


def test_drop_statements(results):
    """Test DROP statements"""
    print("\n" + "=" * 70)
    print("Testing DROP Statements")
    print("=" * 70)

    # DROP TABLE
    results.test("DROP TABLE",
        "DROP TABLE users",
        DropTableStatement)

    # DROP TABLE IF EXISTS
    results.test("DROP TABLE IF EXISTS",
        "DROP TABLE IF EXISTS users",
        DropTableStatement)

    # DROP INDEX
    results.test("DROP INDEX",
        "DROP INDEX idx_users_email",
        DropIndexStatement)

    # DROP VIEW
    results.test("DROP VIEW",
        "DROP VIEW active_users",
        DropViewStatement)

    # DROP TRIGGER
    results.test("DROP TRIGGER",
        "DROP TRIGGER update_modified",
        DropTriggerStatement)


def test_transaction_statements(results):
    """Test transaction control statements"""
    print("\n" + "=" * 70)
    print("Testing Transaction Statements")
    print("=" * 70)

    # BEGIN
    results.test("BEGIN",
        "BEGIN",
        BeginStatement)

    # BEGIN TRANSACTION
    results.test("BEGIN TRANSACTION",
        "BEGIN TRANSACTION",
        BeginStatement)

    # BEGIN DEFERRED
    results.test("BEGIN DEFERRED",
        "BEGIN DEFERRED TRANSACTION",
        BeginStatement)

    # BEGIN IMMEDIATE
    results.test("BEGIN IMMEDIATE",
        "BEGIN IMMEDIATE",
        BeginStatement)

    # BEGIN EXCLUSIVE
    results.test("BEGIN EXCLUSIVE",
        "BEGIN EXCLUSIVE",
        BeginStatement)

    # COMMIT
    results.test("COMMIT",
        "COMMIT",
        CommitStatement)

    # END
    results.test("END",
        "END TRANSACTION",
        CommitStatement)

    # ROLLBACK
    results.test("ROLLBACK",
        "ROLLBACK",
        RollbackStatement)

    # ROLLBACK TO SAVEPOINT
    results.test("ROLLBACK TO SAVEPOINT",
        "ROLLBACK TO SAVEPOINT sp1",
        RollbackStatement)

    # SAVEPOINT
    results.test("SAVEPOINT",
        "SAVEPOINT sp1",
        SavepointStatement)

    # RELEASE SAVEPOINT
    results.test("RELEASE SAVEPOINT",
        "RELEASE SAVEPOINT sp1",
        ReleaseStatement)


def test_database_management_statements(results):
    """Test database management statements"""
    print("\n" + "=" * 70)
    print("Testing Database Management Statements")
    print("=" * 70)

    # ATTACH DATABASE
    results.test("ATTACH DATABASE",
        "ATTACH DATABASE 'other.db' AS other",
        AttachStatement)

    # DETACH DATABASE
    results.test("DETACH DATABASE",
        "DETACH DATABASE other",
        DetachStatement)

    # ANALYZE
    results.test("ANALYZE",
        "ANALYZE",
        AnalyzeStatement)

    # ANALYZE table
    results.test("ANALYZE table",
        "ANALYZE users",
        AnalyzeStatement)

    # VACUUM
    results.test("VACUUM",
        "VACUUM",
        VacuumStatement)

    # VACUUM INTO
    results.test("VACUUM INTO",
        "VACUUM INTO 'backup.db'",
        VacuumStatement)

    # REINDEX
    results.test("REINDEX",
        "REINDEX",
        ReindexStatement)

    # REINDEX table
    results.test("REINDEX table",
        "REINDEX users",
        ReindexStatement)

    # EXPLAIN
    results.test("EXPLAIN",
        "EXPLAIN SELECT * FROM users",
        ExplainStatement)

    # EXPLAIN QUERY PLAN
    results.test("EXPLAIN QUERY PLAN",
        "EXPLAIN QUERY PLAN SELECT * FROM users WHERE id = 1",
        ExplainStatement)

    # PRAGMA
    results.test("PRAGMA",
        "PRAGMA table_info(users)",
        PragmaStatement)

    # PRAGMA assignment
    results.test("PRAGMA assignment",
        "PRAGMA foreign_keys = ON",
        PragmaStatement)


def test_window_functions(results):
    """Test window functions"""
    print("\n" + "=" * 70)
    print("Testing Window Functions")
    print("=" * 70)

    # ROW_NUMBER
    results.test("ROW_NUMBER",
        "SELECT ROW_NUMBER() OVER (ORDER BY created_at) FROM users",
        SelectStatement)

    # PARTITION BY
    results.test("PARTITION BY",
        "SELECT country, ROW_NUMBER() OVER (PARTITION BY country ORDER BY name) FROM users",
        SelectStatement)

    # ROWS frame
    results.test("ROWS frame",
        "SELECT SUM(amount) OVER (ORDER BY date ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM transactions",
        SelectStatement)

    # RANGE frame
    results.test("RANGE frame",
        "SELECT AVG(price) OVER (ORDER BY date RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM prices",
        SelectStatement)


def test_expressions(results):
    """Test various expressions"""
    print("\n" + "=" * 70)
    print("Testing Expressions")
    print("=" * 70)

    # CASE expression
    results.test("CASE expression",
        "SELECT CASE WHEN age < 18 THEN 'minor' ELSE 'adult' END FROM users",
        SelectStatement)

    # CAST expression
    results.test("CAST expression",
        "SELECT CAST(price AS INTEGER) FROM products",
        SelectStatement)

    # BETWEEN
    results.test("BETWEEN",
        "SELECT * FROM users WHERE age BETWEEN 18 AND 65",
        SelectStatement)

    # IN with list
    results.test("IN list",
        "SELECT * FROM users WHERE country IN ('US', 'UK', 'CA')",
        SelectStatement)

    # IN with subquery
    results.test("IN subquery",
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
        SelectStatement)

    # LIKE
    results.test("LIKE",
        "SELECT * FROM users WHERE email LIKE '%@example.com'",
        SelectStatement)

    # GLOB
    results.test("GLOB",
        "SELECT * FROM files WHERE name GLOB '*.txt'",
        SelectStatement)

    # IS NULL
    results.test("IS NULL",
        "SELECT * FROM users WHERE deleted_at IS NULL",
        SelectStatement)

    # IS NOT NULL
    results.test("IS NOT NULL",
        "SELECT * FROM users WHERE email IS NOT NULL",
        SelectStatement)

    # EXISTS
    results.test("EXISTS",
        "SELECT * FROM users WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)",
        SelectStatement)

    # COLLATE
    results.test("COLLATE",
        "SELECT * FROM users ORDER BY name COLLATE NOCASE",
        SelectStatement)


def test_functions(results):
    """Test function calls"""
    print("\n" + "=" * 70)
    print("Testing Functions")
    print("=" * 70)

    # Aggregate functions
    results.test("COUNT(*)",
        "SELECT COUNT(*) FROM users",
        SelectStatement)

    results.test("COUNT DISTINCT",
        "SELECT COUNT(DISTINCT country) FROM users",
        SelectStatement)

    results.test("SUM",
        "SELECT SUM(amount) FROM transactions",
        SelectStatement)

    results.test("AVG",
        "SELECT AVG(age) FROM users",
        SelectStatement)

    results.test("MIN/MAX",
        "SELECT MIN(price), MAX(price) FROM products",
        SelectStatement)

    # String functions
    results.test("LOWER",
        "SELECT LOWER(name) FROM users",
        SelectStatement)

    results.test("UPPER",
        "SELECT UPPER(email) FROM users",
        SelectStatement)

    results.test("SUBSTR",
        "SELECT SUBSTR(name, 1, 10) FROM users",
        SelectStatement)

    # Date functions
    results.test("DATE",
        "SELECT DATE('now') FROM users",
        SelectStatement)

    results.test("DATETIME",
        "SELECT DATETIME('now', '+1 day') FROM users",
        SelectStatement)

    # Math functions
    results.test("ROUND",
        "SELECT ROUND(price, 2) FROM products",
        SelectStatement)

    results.test("ABS",
        "SELECT ABS(balance) FROM accounts",
        SelectStatement)


def test_complex_queries(results):
    """Test complex real-world queries"""
    print("\n" + "=" * 70)
    print("Testing Complex Queries")
    print("=" * 70)

    # Complex join with aggregation
    results.test("Complex join aggregation",
        """SELECT u.name, COUNT(o.id) as order_count, SUM(o.total) as total_spent
           FROM users u
           LEFT JOIN orders o ON u.id = o.user_id
           WHERE u.created_at > '2020-01-01'
           GROUP BY u.id, u.name
           HAVING order_count > 5
           ORDER BY total_spent DESC
           LIMIT 100""",
        SelectStatement)

    # CTE with multiple references
    results.test("CTE multiple refs",
        """WITH monthly_sales AS (
               SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
               FROM sales
               GROUP BY month
           )
           SELECT m1.month, m1.total, m1.total - m2.total as growth
           FROM monthly_sales m1
           LEFT JOIN monthly_sales m2 ON m1.month = date(m2.month, '+1 month')""",
        SelectStatement)

    # Nested subqueries
    results.test("Nested subqueries",
        """SELECT *
           FROM users
           WHERE id IN (
               SELECT user_id FROM orders WHERE total > (
                   SELECT AVG(total) FROM orders
               )
           )""",
        SelectStatement)


def main():
    """Run all tests"""
    print("\n" + "#" * 70)
    print("# SQLite Parser - Comprehensive Test Suite")
    print("# Testing ALL statement types from SQLite reference")
    print("#" * 70)

    results = TestResults()

    # Run all test suites
    test_select_statements(results)
    test_cte_statements(results)
    test_insert_statements(results)
    test_update_statements(results)
    test_delete_statements(results)
    test_create_table_statements(results)
    test_alter_table_statements(results)
    test_create_index_statements(results)
    test_create_view_statements(results)
    test_create_trigger_statements(results)
    test_drop_statements(results)
    test_transaction_statements(results)
    test_database_management_statements(results)
    test_window_functions(results)
    test_expressions(results)
    test_functions(results)
    test_complex_queries(results)

    # Print summary
    results.summary()

    return results.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
