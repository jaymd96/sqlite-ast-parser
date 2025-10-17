# sqlite-ast-parser

A complete, production-ready SQLite SQL parser in Python that returns detailed Abstract Syntax Trees (AST) for all SQLite SQL statements.

## Features

- **Complete SQLite Coverage**: Supports all SQLite statements (SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, transactions, etc.)
- **Comprehensive AST**: Detailed AST nodes for every SQL construct
- **Position Tracking**: All tokens and nodes include line/column information for error reporting
- **Error Recovery**: Collects multiple errors and provides helpful error messages
- **Pure Python**: No external dependencies
- **Production Quality**: Robust error handling and comprehensive node definitions

## Architecture

The parser follows a scanner-buffer lexer and recursive descent parser design using precedence climbing for expressions.

### Components

1. **Lexer** (`lexer.py`): Mode-driven tokenizer
   - Handles strings, identifiers, comments, operators, keywords
   - Position tracking for every token
   - Multiple modes (NORMAL, STRING, COMMENT, etc.)

2. **Parser** (`parser.py`): Recursive descent parser
   - Precedence climbing for expressions
   - Error recovery with synchronization points
   - Comprehensive support for all SQLite statements

3. **AST Nodes** (`ast_nodes.py`): Complete node definitions
   - 80+ node types covering all SQLite constructs
   - Position information on every node
   - Dataclasses for easy manipulation

4. **Error Handling** (`errors.py`): Production-quality errors
   - Position-aware error messages
   - Context snippets showing error location
   - Multiple error collection

5. **Utilities** (`utils.py`): Constants and helpers
   - All 147 SQLite keywords
   - Operator precedence table
   - Token type definitions

## Installation

```bash
pip install sqlite-ast-parser
```

No external dependencies needed - pure Python!

## Usage

### Basic Parsing

```python
from sqlite_parser import parse_sql

# Parse a SQL statement
sql = "SELECT * FROM users WHERE age > 18"
ast = parse_sql(sql)

# ast is a list of Statement nodes
for statement in ast:
    print(statement)
```

### Tokenization Only

```python
from sqlite_parser import tokenize_sql

sql = "SELECT id, name FROM users"
tokens = tokenize_sql(sql)

for token in tokens:
    print(f"{token.type}: {token.value} at {token.position}")
```

### Error Handling

```python
from sqlite_parser import parse_sql
from sqlite_parser.errors import ParseError

try:
    ast = parse_sql("SELECT FROM")  # Invalid SQL
except ParseError as e:
    print(f"Parse error: {e}")
    # Output includes line/column and context
```

## AST Structure

### Statement Nodes

The parser returns a list of `Statement` nodes. Main statement types:

#### Data Manipulation (DML)
- `SelectStatement` - SELECT queries (including compound SELECTs with UNION/INTERSECT/EXCEPT)
- `InsertStatement` - INSERT/REPLACE statements
- `UpdateStatement` - UPDATE statements
- `DeleteStatement` - DELETE statements

#### Data Definition (DDL)
- `CreateTableStatement` - CREATE TABLE
- `AlterTableStatement` - ALTER TABLE (RENAME, ADD/DROP COLUMN)
- `CreateIndexStatement` - CREATE INDEX
- `CreateViewStatement` - CREATE VIEW
- `CreateTriggerStatement` - CREATE TRIGGER
- `CreateVirtualTableStatement` - CREATE VIRTUAL TABLE
- `Drop*Statement` - DROP TABLE/INDEX/VIEW/TRIGGER

#### Transaction Control
- `BeginStatement` - BEGIN TRANSACTION
- `CommitStatement` - COMMIT
- `RollbackStatement` - ROLLBACK
- `SavepointStatement` - SAVEPOINT
- `ReleaseStatement` - RELEASE SAVEPOINT

#### Database Management
- `AttachStatement` - ATTACH DATABASE
- `DetachStatement` - DETACH DATABASE
- `AnalyzeStatement` - ANALYZE
- `VacuumStatement` - VACUUM
- `ReindexStatement` - REINDEX
- `ExplainStatement` - EXPLAIN [QUERY PLAN]
- `PragmaStatement` - PRAGMA

### Expression Nodes

All expressions inherit from `Expression`. Main types:

#### Literals
- `NumberLiteral` - integers and floats
- `StringLiteral` - string constants
- `BlobLiteral` - BLOB literals (X'hex')
- `NullLiteral` - NULL
- `BooleanLiteral` - TRUE/FALSE
- `CurrentTimeLiteral` - CURRENT_TIME/DATE/TIMESTAMP

#### Identifiers
- `Identifier` - simple column/table names
- `QualifiedIdentifier` - schema.table.column
- `Parameter` - placeholders (?123, :name, @name, $name)

#### Operators
- `UnaryExpression` - unary +, -, NOT, ~
- `BinaryExpression` - arithmetic, comparison, logical, bitwise
- `BetweenExpression` - BETWEEN ... AND ...
- `InExpression` - IN (values) or IN (subquery)
- `LikeExpression` - LIKE/GLOB/REGEXP/MATCH

#### Functions and Special
- `FunctionCall` - function calls with DISTINCT, FILTER, OVER
- `CaseExpression` - CASE WHEN ... THEN ... ELSE ... END
- `CastExpression` - CAST(expr AS type)
- `CollateExpression` - expr COLLATE collation
- `ExistsExpression` - EXISTS (subquery)
- `SubqueryExpression` - (SELECT ...)
- `WindowExpression` - OVER (PARTITION BY ... ORDER BY ... ROWS/RANGE ...)

### Example AST

```python
sql = "SELECT id, name FROM users WHERE age > 18"
ast = parse_sql(sql)

# ast[0] is a SelectStatement with:
# - select_core.columns: [ResultColumn(Identifier("id")), ResultColumn(Identifier("name"))]
# - select_core.from_clause: FromClause(TableReference("users"))
# - select_core.where: WhereClause(BinaryExpression(>, Identifier("age"), NumberLiteral(18)))
```

## Implementation Status

### ✅ Complete
- Complete AST node definitions (80+ types)
- Full lexer implementation (tokenization)
- Full parser implementation (all SQLite statements)
- Error classes with position tracking
- Utility functions and constants (147 keywords, precedence table)
- Public API in `__init__.py`
- Comprehensive test suite (127 tests, 100% pass rate)
- Example scripts and debugging utilities

## Development Guide

### Adding New Statement Types

1. Define AST node in `ast_nodes.py`
2. Add parsing method in `parser.py`
3. Add tests in `tests/`

Example:
```python
# In ast_nodes.py
@dataclass
class MyStatement(Statement):
    field1: str
    field2: Expression

# In parser.py
def parse_my_statement(self) -> MyStatement:
    self.expect(TokenType.MY_KEYWORD)
    field1 = self.consume(TokenType.IDENTIFIER).value
    field2 = self.parse_expression()
    return MyStatement(field1=field1, field2=field2)
```

### Extending the Parser

The parser uses recursive descent with these key methods:

- `peek(n)` - look ahead n tokens
- `match(*types)` - check if current token matches
- `consume(type)` - advance if matches, else error
- `expect(type)` - consume with detailed error message

Expression parsing uses precedence climbing:

- `parse_expression()` - entry point
- `parse_binary_expression(min_prec)` - handles operator precedence
- `parse_primary_expression()` - literals, identifiers, function calls

### Testing

```python
# Example test
def test_select_statement():
    sql = "SELECT * FROM users"
    ast = parse_sql(sql)
    assert len(ast) == 1
    assert isinstance(ast[0], SelectStatement)
    assert ast[0].select_core.columns[0].expression is None  # * means no expression
```

## Documentation

Additional documentation is available in the `docs/` directory:
- `docs/sqlite_syntax_reference.md` - Complete SQLite syntax reference
- `docs/lexer+parser_mental_model.md` - Conceptual foundation of the lexer and parser design
- `docs/IMPLEMENTATION_COMPLETE.md` - Implementation details
- `docs/TEST_RESULTS.md` - Test results and coverage

## Implementation Notes

### Lexer Design

The lexer follows a mode-driven scanner-buffer model:

**Modes:**
- `NORMAL` - default SQL parsing
- `STRING_SINGLE` - inside 'string'
- `STRING_DOUBLE` - inside "identifier"
- `BLOCK_COMMENT` - inside /* comment */
- `LINE_COMMENT` - inside -- comment
- `BRACKET_IDENTIFIER` - inside [identifier]
- `BACKTICK_IDENTIFIER` - inside `identifier`

**Core Operations:**
- `peek(n)` - look ahead n characters
- `advance()` - consume character, add to buffer
- `skip()` - consume without buffering
- `emit(type)` - create token with position
- `error(msg)` - report lexer error

### Parser Design

The parser uses recursive descent with precedence climbing for expressions:

**Expression Precedence (low to high):**
1. OR
2. AND
3. NOT
4. Comparison (=, <, >, <=, >=, !=, <>, IS, IN, LIKE, BETWEEN)
5. Bitwise (<<, >>, &, |)
6. Addition (+, -, ||)
7. Multiplication (*, /, %)
8. COLLATE
9. Unary (+, -, NOT, ~)
10. Primary (literals, identifiers, function calls, subqueries)

**Error Recovery:**
- Panic mode: skip to synchronization points (semicolon, keywords)
- Error nodes: placeholder nodes to continue parsing
- Multiple error collection: don't stop at first error

### Special SQLite Features

- **Case Insensitivity**: Keywords are case-insensitive
- **Optional Semicolons**: Statements don't require semicolons
- **Flexible Quoting**: Identifiers can use ", ', [], or `
- **Parameters**: Supports ?, ?N, :name, @name, $name
- **Comments**: Both -- line comments and /* block comments */
- **BLOB Literals**: X'hexadecimal'
- **WITHOUT ROWID**: Special table option
- **STRICT**: Type enforcement option
- **Generated Columns**: GENERATED ALWAYS AS (expr) STORED/VIRTUAL

## Performance Considerations

- Lexer uses character-by-character scanning with lookahead
- Parser uses recursive descent (no backtracking except for disambiguation)
- Expression parsing uses precedence climbing (O(n) for expressions)
- No AST optimization passes (returns raw parse tree)

## Limitations

- Does not validate semantic correctness (e.g., column existence)
- Does not resolve identifier scope
- Does not perform type checking
- Does not optimize or transform the AST
- Parser may accept some syntactically invalid SQL that SQLite would reject


## References

- SQLite Official Docs: https://sqlite.org/lang.html
- SQLite Syntax Diagrams: https://sqlite.org/syntax.html
- See `docs/` directory for additional documentation

## Project Structure

```
SqliteASTParser/
├── README.md                          # This file
├── sqlite_syntax_reference.md         # Complete SQLite syntax reference
├── lexer+parser_mental_model.md      # Design mental model
├── sqlite_parser/                     # Main package
│   ├── __init__.py                    # Public API
│   ├── ast_nodes.py                   # AST node definitions (✅ Complete)
│   ├── errors.py                      # Error classes (✅ Complete)
│   ├── utils.py                       # Constants and helpers (✅ Complete)
│   ├── lexer.py                       # Tokenizer (🚧 In progress)
│   └── parser.py                      # Parser (🚧 In progress)
├── tests/                             # Test suite
│   ├── test_lexer.py
│   ├── test_parser_select.py
│   ├── test_parser_dml.py
│   ├── test_parser_ddl.py
│   └── test_integration.py
└── examples/                          # Example scripts
    ├── basic_usage.py
    ├── ast_traversal.py
    └── pretty_print.py
```

## Testing

The parser includes a comprehensive test suite with 127 tests covering all SQLite statement types:

```bash
pytest tests/ -v
```

Or run the full test suite:

```bash
python tests/test_all_statements.py
```

## Contributing

Contributions welcome! Areas for potential improvement:
- Additional test cases for edge cases
- Performance optimizations
- Semantic analysis capabilities
- Pretty printer to format AST back to SQL
- AST transformation utilities

## License

MIT License - see LICENSE file for details.
