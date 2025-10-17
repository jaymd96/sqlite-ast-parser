# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-17

### Added
- Initial release of sqlite-ast-parser
- Complete SQLite SQL parser with comprehensive AST generation
- Support for all major SQLite statement types:
  - DDL: CREATE TABLE, CREATE INDEX, CREATE VIEW, CREATE TRIGGER, ALTER TABLE, DROP statements
  - DML: SELECT, INSERT, UPDATE, DELETE, REPLACE
  - Query constructs: JOIN, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET
  - Advanced features: CTEs, window functions, compound queries (UNION/INTERSECT/EXCEPT)
  - PRAGMA statements
  - Transaction control: BEGIN, COMMIT, ROLLBACK, SAVEPOINT, RELEASE
- Comprehensive operator support including special operators (BETWEEN, IN, LIKE, GLOB, MATCH, REGEXP)
- Detailed position tracking for all AST nodes
- Type-safe AST node classes with dataclass support
- Debugging utilities for parser state inspection
- Interactive test CLI with multiple verbosity levels
- 127 comprehensive tests covering all statement types (100% pass rate)

### Technical Features
- Recursive descent parser with precedence climbing for expressions
- Proper operator precedence handling
- Window function frame specifications (ROWS, RANGE, GROUPS)
- Trigger support with OLD/NEW qualified identifiers
- Foreign key constraints and table constraints
- Index specifications with expressions and WHERE clauses
- View materialization options
- Conflict resolution clauses (ROLLBACK, ABORT, FAIL, IGNORE, REPLACE)

[0.1.0]: https://github.com/yourusername/sqlite-ast-parser/releases/tag/v0.1.0
