#> # AST Node Definitions
#
# This module defines the **complete Abstract Syntax Tree (AST) schema** for SQLite SQL.
# With 80+ node types, it represents every SQL construct that SQLite supports.
#
# ## Design Philosophy
#
# The AST design follows these principles:
#
# 1. **Type Safety**: Using Python dataclasses with type hints ensures correctness
# 2. **Completeness**: Every SQL construct has a dedicated node type
# 3. **Position Tracking**: All nodes include source span information for error reporting
# 4. **Hierarchy**: Clear inheritance from base classes (Statement, Expression, Clause)
# 5. **Immutability**: Dataclasses encourage treating AST as immutable data
#
# ## Node Categories
#
# The AST is organized into logical sections:
#
# - **Position & Base Classes**: Foundation for all nodes
# - **Enums**: Type-safe representations of SQL keywords and options
# - **Literals**: Numbers, strings, blobs, NULL, booleans, timestamps
# - **Identifiers**: Simple and qualified names, parameters
# - **Expressions**: Operators, function calls, CASE, CAST, etc.
# - **Clauses**: WHERE, ORDER BY, GROUP BY, LIMIT, etc.
# - **Statements**: SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, etc.
#
# ## Usage Pattern
#
# When the parser encounters SQL like `SELECT id FROM users WHERE age > 18`, it builds:
#
# ```python
# SelectStatement(
#     select_core=SelectCore(
#         columns=[ResultColumn(Identifier("id"))],
#         from_clause=FromClause(TableReference(QualifiedIdentifier(["users"]))),
#         where=WhereClause(BinaryExpression(">", Identifier("age"), NumberLiteral(18)))
#     )
# )
# ```

"""
AST Node Definitions for SQLite SQL Parser

This module defines all Abstract Syntax Tree node types for representing
SQLite SQL statements, expressions, clauses, and definitions.

Each node includes position information for error reporting and debugging.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any, Union
from enum import Enum, auto

#> ## Position Tracking
#
# Every AST node can optionally include a `Span` that records its **exact location**
# in the source code. This enables precise error messages and syntax highlighting.
#
# ### Position
#
# A `Position` represents a single point in the source:
# - `line`: 1-based line number
# - `column`: 1-based column number
# - `offset`: 0-based character offset from start
#
# ### Span
#
# A `Span` represents a range using start and end positions, tracking the full
# extent of each syntax element.

# ==============================================================================
# Position and Base Classes
# ==============================================================================

@dataclass
class Position:
    """Position in source code"""
    line: int
    column: int
    offset: int  # character offset from start

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass
class Span:
    """Source code span"""
    start: Position
    end: Position

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


#> ## Base AST Classes
#
# These four classes form the **foundation** of the AST hierarchy:
#
# ### ASTNode
#
# The root of all AST nodes. Every node optionally tracks its source `span` for
# position-aware error messages and IDE features. The custom `__repr__` omits spans
# for cleaner debug output.
#
# ### Statement
#
# Represents complete SQL statements like SELECT, INSERT, CREATE TABLE. Statements
# are top-level constructs that can be executed independently.
#
# ### Expression
#
# Represents values and computations: literals, identifiers, operators, function calls,
# subqueries. Expressions produce values and can be nested.
#
# ### Clause
#
# Represents named parts of statements: WHERE, ORDER BY, GROUP BY, LIMIT.
# Clauses organize related syntax within statements.

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    span: Optional[Span] = field(default=None, kw_only=True)

    def __repr__(self) -> str:
        fields = [f"{k}={repr(v)}" for k, v in self.__dict__.items() if k != 'span']
        return f"{self.__class__.__name__}({', '.join(fields)})"


@dataclass
class Statement(ASTNode):
    """Base class for all SQL statements"""
    pass


@dataclass
class Expression(ASTNode):
    """Base class for all expressions"""
    pass


@dataclass
class Clause(ASTNode):
    """Base class for all clauses"""
    pass

#> ## SQL Construct Enumerations
#
# These enums provide **type-safe representations** of SQL keywords and options.
# Using enums instead of strings prevents typos and enables IDE autocomplete.
#
# The enums cover:
# - **JoinType**: INNER, LEFT, RIGHT, FULL, CROSS
# - **Operators**: Unary (+, -, NOT, ~) and Binary (+, -, *, /, =, <, >, AND, OR, etc.)
# - **CompoundOperator**: UNION, INTERSECT, EXCEPT
# - **ConflictResolution**: ROLLBACK, ABORT, FAIL, IGNORE, REPLACE
# - **TransactionType**: DEFERRED, IMMEDIATE, EXCLUSIVE
# - **TriggerTiming**: BEFORE, AFTER, INSTEAD OF
# - **OrderDirection**: ASC, DESC
# - **FrameType**: ROWS, RANGE, GROUPS (for window functions)
#
# Each enum value includes its SQL string representation for code generation.

# ==============================================================================
# Enums for Various SQL Constructs
# ==============================================================================

class JoinType(Enum):
    """Types of SQL joins"""
    INNER = auto()
    LEFT = auto()
    RIGHT = auto()
    FULL = auto()
    CROSS = auto()


class UnaryOperator(Enum):
    """Unary operators"""
    PLUS = "+"
    MINUS = "-"
    NOT = "NOT"
    BITNOT = "~"


class BinaryOperator(Enum):
    """Binary operators"""
    # Arithmetic
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"

    # Comparison
    EQUAL = "="
    EQUAL2 = "=="
    NOT_EQUAL = "!="
    NOT_EQUAL2 = "<>"
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="

    # Logical
    AND = "AND"
    OR = "OR"

    # Bitwise
    BIT_AND = "&"
    BIT_OR = "|"
    LEFT_SHIFT = "<<"
    RIGHT_SHIFT = ">>"

    # String
    CONCAT = "||"

    # Special
    IS = "IS"
    IS_NOT = "IS NOT"
    IN = "IN"
    NOT_IN = "NOT IN"
    LIKE = "LIKE"
    NOT_LIKE = "NOT LIKE"
    GLOB = "GLOB"
    NOT_GLOB = "NOT GLOB"
    MATCH = "MATCH"
    NOT_MATCH = "NOT MATCH"
    REGEXP = "REGEXP"
    NOT_REGEXP = "NOT REGEXP"


class CompoundOperator(Enum):
    """Compound SELECT operators"""
    UNION = "UNION"
    UNION_ALL = "UNION ALL"
    INTERSECT = "INTERSECT"
    EXCEPT = "EXCEPT"


class ConflictResolution(Enum):
    """Conflict resolution algorithms"""
    ROLLBACK = "ROLLBACK"
    ABORT = "ABORT"
    FAIL = "FAIL"
    IGNORE = "IGNORE"
    REPLACE = "REPLACE"


class TransactionType(Enum):
    """Transaction types"""
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"


class TriggerTiming(Enum):
    """Trigger timing"""
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    INSTEAD_OF = "INSTEAD OF"


class TriggerEvent(Enum):
    """Trigger events"""
    DELETE = "DELETE"
    INSERT = "INSERT"
    UPDATE = "UPDATE"


class OrderDirection(Enum):
    """ORDER BY direction"""
    ASC = "ASC"
    DESC = "DESC"


class NullsOrdering(Enum):
    """NULLS ordering"""
    FIRST = "FIRST"
    LAST = "LAST"


class FrameType(Enum):
    """Window frame type"""
    ROWS = "ROWS"
    RANGE = "RANGE"
    GROUPS = "GROUPS"


class FrameBound(Enum):
    """Window frame boundary"""
    UNBOUNDED_PRECEDING = "UNBOUNDED PRECEDING"
    PRECEDING = "PRECEDING"
    CURRENT_ROW = "CURRENT ROW"
    FOLLOWING = "FOLLOWING"
    UNBOUNDED_FOLLOWING = "UNBOUNDED FOLLOWING"


#> ## Literal Expressions
#
# Literals represent **constant values** in SQL. Each literal type preserves both the
# parsed value and metadata about how it was written:
#
# - **NumberLiteral**: Integers (42) and floats (3.14, 1.5e10). Stores both the numeric
#   value and original text to preserve precision and formatting.
#
# - **StringLiteral**: Text in single ('text') or double quotes ("text"). Records which
#   quote character was used.
#
# - **BlobLiteral**: Binary data as hex (X'48656C6C6F'). Stores decoded bytes and
#   original hex string.
#
# - **NullLiteral**: The NULL keyword, representing absence of value.
#
# - **BooleanLiteral**: TRUE or FALSE keywords (SQLite extension).
#
# - **CurrentTimeLiteral**: CURRENT_TIME, CURRENT_DATE, or CURRENT_TIMESTAMP for
#   database-provided timestamps.
#
# All literals inherit from `Expression`, making them usable anywhere an expression
# is expected.

# ==============================================================================
# Literal Expressions
# ==============================================================================

@dataclass
class NumberLiteral(Expression):
    """Numeric literal (integer or float)"""
    value: Union[int, float]
    raw: str  # original text representation


@dataclass
class StringLiteral(Expression):
    """String literal"""
    value: str
    quote_char: str  # ' or "


@dataclass
class BlobLiteral(Expression):
    """BLOB literal (X'hex')"""
    value: bytes
    raw: str  # original hex string


@dataclass
class NullLiteral(Expression):
    """NULL literal"""
    pass


@dataclass
class BooleanLiteral(Expression):
    """Boolean literal (TRUE/FALSE)"""
    value: bool


@dataclass
class CurrentTimeLiteral(Expression):
    """CURRENT_TIME, CURRENT_DATE, CURRENT_TIMESTAMP"""
    type: str  # TIME, DATE, or TIMESTAMP

#> ## Identifiers and References
#
# Identifiers name database objects and values:
#
# ### Identifier
#
# A simple name like `users` or `age`. Records whether it was quoted (allowing spaces
# and keywords as names): `[user name]`, `"table"`, `` `column` ``.
#
# ### QualifiedIdentifier
#
# A dot-separated name like `schema.table.column` or `table.column`. Provides convenient
# properties (`schema`, `table`, `column`) to access parts without manual indexing.
#
# Examples:
# - `users` → parts=["users"]
# - `users.id` → parts=["users", "id"] (table.column)
# - `main.users.id` → parts=["main", "users", "id"] (schema.table.column)
#
# ### Parameter
#
# A placeholder for bound values:
# - Positional: `?` or `?1`, `?2`, ...
# - Named: `:name`, `@name`, `$name`
#
# Used in prepared statements to safely insert user data.

# ==============================================================================
# Identifiers and References
# ==============================================================================

@dataclass
class Identifier(Expression):
    """Simple identifier"""
    name: str
    quoted: bool = False  # whether it was quoted in source


@dataclass
class QualifiedIdentifier(Expression):
    """Qualified identifier (schema.table.column)"""
    parts: List[str]  # [schema, table, column] or [table, column] or [schema, table]

    @property
    def schema(self) -> Optional[str]:
        return self.parts[0] if len(self.parts) == 3 else None

    @property
    def table(self) -> Optional[str]:
        if len(self.parts) == 3:
            return self.parts[1]
        elif len(self.parts) == 2:
            return self.parts[0]
        return None

    @property
    def column(self) -> str:
        return self.parts[-1]


@dataclass
class Parameter(Expression):
    """Parameter placeholder (?123, :name, @name, $name)"""
    name: Optional[str] = None  # None for ? or ?123
    number: Optional[int] = None  # for ?123
    prefix: str = "?"  # ?, :, @, or $


# ==============================================================================
# Unary and Binary Expressions
# ==============================================================================

@dataclass
class UnaryExpression(Expression):
    """Unary expression"""
    operator: UnaryOperator
    operand: Expression


@dataclass
class BinaryExpression(Expression):
    """Binary expression"""
    operator: BinaryOperator
    left: Expression
    right: Expression


@dataclass
class BetweenExpression(Expression):
    """BETWEEN expression"""
    value: Expression
    lower: Expression
    upper: Expression
    negated: bool = False  # NOT BETWEEN


@dataclass
class InExpression(Expression):
    """IN expression"""
    value: Expression
    values: Union[List[Expression], 'SubqueryExpression']  # list or subquery
    negated: bool = False  # NOT IN


@dataclass
class LikeExpression(Expression):
    """LIKE/GLOB/REGEXP/MATCH expression"""
    value: Expression
    pattern: Expression
    operator: str  # LIKE, GLOB, REGEXP, or MATCH
    escape: Optional[Expression] = None  # ESCAPE clause
    negated: bool = False


# ==============================================================================
# Function Calls and Special Expressions
# ==============================================================================

@dataclass
class FunctionCall(Expression):
    """Function call"""
    name: str
    args: List[Expression]
    distinct: bool = False  # DISTINCT keyword
    star: bool = False  # COUNT(*)
    filter_clause: Optional['WhereClause'] = None  # FILTER (WHERE ...)
    over_clause: Optional['WindowExpression'] = None  # OVER (...)


@dataclass
class CaseExpression(Expression):
    """CASE expression"""
    value: Optional[Expression] = None  # for CASE value WHEN ...
    when_clauses: List[tuple[Expression, Expression]] = field(default_factory=list)  # [(condition, result), ...]
    else_clause: Optional[Expression] = None


@dataclass
class CastExpression(Expression):
    """CAST expression"""
    expression: Expression
    type_name: str


@dataclass
class CollateExpression(Expression):
    """COLLATE expression"""
    expression: Expression
    collation: str


@dataclass
class ExistsExpression(Expression):
    """EXISTS expression"""
    subquery: 'SubqueryExpression'


@dataclass
class SubqueryExpression(Expression):
    """Subquery in parentheses"""
    select: 'SelectStatement'


@dataclass
class ParenthesizedExpression(Expression):
    """Expression in parentheses (not a subquery)"""
    expression: Expression


@dataclass
class RaiseExpression(Expression):
    """RAISE expression (for triggers only)"""
    raise_type: str  # IGNORE, ROLLBACK, ABORT, or FAIL
    message: Optional[str] = None  # error message (not used for IGNORE)


# ==============================================================================
# Window Functions
# ==============================================================================

@dataclass
class WindowExpression(Expression):
    """Window specification (OVER clause)"""
    window_name: Optional[str] = None  # named window
    partition_by: List[Expression] = field(default_factory=list)
    order_by: List['OrderingTerm'] = field(default_factory=list)
    frame_spec: Optional['FrameSpec'] = None


@dataclass
class FrameSpec(ASTNode):
    """Window frame specification"""
    frame_type: FrameType  # ROWS, RANGE, or GROUPS
    start: 'FrameBoundary'
    end: Optional['FrameBoundary'] = None  # None means CURRENT ROW


@dataclass
class FrameBoundary(ASTNode):
    """Window frame boundary"""
    bound_type: FrameBound
    offset: Optional[Expression] = None  # for PRECEDING/FOLLOWING with offset


# ==============================================================================
# Common Clauses
# ==============================================================================

@dataclass
class WhereClause(Clause):
    """WHERE clause"""
    condition: Expression


@dataclass
class OrderByClause(Clause):
    """ORDER BY clause"""
    terms: List['OrderingTerm']


@dataclass
class OrderingTerm(ASTNode):
    """Single ORDER BY term"""
    expression: Expression
    direction: Optional[OrderDirection] = None
    nulls: Optional[NullsOrdering] = None


@dataclass
class GroupByClause(Clause):
    """GROUP BY clause"""
    expressions: List[Expression]
    having: Optional['HavingClause'] = None


@dataclass
class HavingClause(Clause):
    """HAVING clause"""
    condition: Expression


@dataclass
class LimitClause(Clause):
    """LIMIT clause"""
    limit: Expression
    offset: Optional[Expression] = None


@dataclass
class ReturningClause(Clause):
    """RETURNING clause"""
    columns: List['ResultColumn']


# ==============================================================================
# SELECT Statement Components
# ==============================================================================

@dataclass
class ResultColumn(ASTNode):
    """Result column in SELECT"""
    expression: Optional[Expression] = None  # None for *
    alias: Optional[str] = None
    table_star: Optional[str] = None  # for table.*


@dataclass
class FromClause(Clause):
    """FROM clause"""
    source: Union['TableReference', 'JoinClause']


@dataclass
class TableReference(ASTNode):
    """Table reference in FROM"""
    name: QualifiedIdentifier
    alias: Optional[str] = None
    indexed_by: Optional[str] = None  # INDEXED BY index_name
    not_indexed: bool = False  # NOT INDEXED


@dataclass
class SubqueryTable(ASTNode):
    """Subquery as table source"""
    select: 'SelectStatement'
    alias: Optional[str] = None


@dataclass
class TableFunctionCall(ASTNode):
    """Table-valued function call"""
    function: FunctionCall
    alias: Optional[str] = None


@dataclass
class JoinClause(ASTNode):
    """JOIN clause"""
    left: Union[TableReference, SubqueryTable, 'JoinClause']
    join_type: Optional[JoinType]  # None for comma join
    right: Union[TableReference, SubqueryTable]
    natural: bool = False
    on_condition: Optional[Expression] = None
    using_columns: List[str] = field(default_factory=list)


@dataclass
class WithClause(Clause):
    """WITH clause (CTE)"""
    recursive: bool
    ctes: List['CommonTableExpression']


@dataclass
class CommonTableExpression(ASTNode):
    """Single CTE"""
    name: str
    columns: List[str] = field(default_factory=list)
    select: 'SelectStatement' = None
    materialized: Optional[bool] = None  # True=MATERIALIZED, False=NOT MATERIALIZED, None=default


#> ## SELECT Statement
#
# The SELECT statement is the **most complex** SQL construct, supporting queries,
# subqueries, joins, aggregation, window functions, and compound queries.
#
# ### Structure
#
# ```
# [WITH ...] SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ...
# [UNION/INTERSECT/EXCEPT SELECT ...]
# [ORDER BY ...] [LIMIT ...]
# ```
#
# ### SelectStatement
#
# The top-level node for any SELECT query. It consists of:
#
# - **with_clause**: Optional CTEs (WITH RECURSIVE name AS ...)
# - **select_core**: The main SELECT...FROM...WHERE...GROUP BY
# - **compound_selects**: Additional SELECT cores connected by UNION/INTERSECT/EXCEPT
# - **order_by**: Global ORDER BY (applies to entire compound query)
# - **limit**: Global LIMIT/OFFSET
#
# ### SelectCore
#
# The core SELECT logic before ORDER BY/LIMIT:
#
# - **distinct/all**: DISTINCT or ALL keyword
# - **columns**: Result columns (expressions with optional aliases)
# - **from_clause**: Tables, joins, or subqueries
# - **where**: Filter conditions
# - **group_by**: Grouping expressions with optional HAVING
# - **window_definitions**: Named windows (WINDOW name AS (...))
#
# ### Compound Queries
#
# Multiple SELECT cores can be combined:
# - UNION [ALL]: Combine results (ALL keeps duplicates)
# - INTERSECT: Common rows
# - EXCEPT: Rows in first but not second

# ==============================================================================
# SELECT Statement
# ==============================================================================

@dataclass
class SelectStatement(Statement):
    """SELECT statement (including compound SELECTs)"""
    with_clause: Optional[WithClause] = None
    select_core: 'SelectCore' = None
    compound_selects: List[tuple[CompoundOperator, 'SelectCore']] = field(default_factory=list)
    order_by: Optional[OrderByClause] = None
    limit: Optional[LimitClause] = None


@dataclass
class SelectCore(ASTNode):
    """Core SELECT (without ORDER BY/LIMIT)"""
    distinct: bool = False  # DISTINCT
    all: bool = False  # ALL
    columns: List[ResultColumn] = field(default_factory=list)
    from_clause: Optional[FromClause] = None
    where: Optional[WhereClause] = None
    group_by: Optional[GroupByClause] = None
    window_definitions: List[tuple[str, WindowExpression]] = field(default_factory=list)  # named windows

#> ## Data Modification Statements (DML)
#
# DML statements modify table data: INSERT, UPDATE, DELETE. They all support:
#
# - **WITH clause**: CTEs can be used in data modification
# - **RETURNING clause**: Return modified rows (SQLite 3.35+)
# - **Conflict resolution**: OR IGNORE, OR REPLACE, OR ROLLBACK, etc.
#
# ### INSERT
#
# Adds rows to a table via:
# - VALUES: Explicit row values `INSERT INTO t VALUES (1, 2), (3, 4)`
# - SELECT: Insert query results `INSERT INTO t SELECT * FROM other`
# - DEFAULT VALUES: Use column defaults `INSERT INTO t DEFAULT VALUES`
#
# Supports UPSERT (ON CONFLICT) for handling primary key/unique violations.
#
# ### UPDATE
#
# Modifies existing rows with SET assignments and optional WHERE filter.
# SQLite extensions: UPDATE FROM (joins) and ORDER BY/LIMIT.
#
# ### DELETE
#
# Removes rows matching WHERE condition. Optional ORDER BY/LIMIT with
# SQLITE_ENABLE_UPDATE_DELETE_LIMIT.

# ==============================================================================
# INSERT Statement
# ==============================================================================

@dataclass
class InsertStatement(Statement):
    """INSERT statement"""
    with_clause: Optional[WithClause] = None
    replace: bool = False  # REPLACE keyword
    conflict_resolution: Optional[ConflictResolution] = None  # OR IGNORE, etc.
    table: QualifiedIdentifier = None
    table_alias: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    values: Optional['ValuesClause'] = None
    select: Optional[SelectStatement] = None
    default_values: bool = False  # DEFAULT VALUES
    upsert_clauses: List['UpsertClause'] = field(default_factory=list)
    returning: Optional[ReturningClause] = None


@dataclass
class ValuesClause(ASTNode):
    """VALUES clause"""
    rows: List[List[Expression]]  # list of value lists


@dataclass
class UpsertClause(ASTNode):
    """UPSERT clause (ON CONFLICT)"""
    conflict_target: Optional['ConflictTarget'] = None
    do_nothing: bool = False  # DO NOTHING
    do_update: Optional['DoUpdateClause'] = None  # DO UPDATE SET ...


@dataclass
class ConflictTarget(ASTNode):
    """Conflict target for UPSERT"""
    indexed_columns: List['IndexedColumn'] = field(default_factory=list)
    where: Optional[WhereClause] = None


@dataclass
class DoUpdateClause(ASTNode):
    """DO UPDATE SET clause"""
    assignments: List['Assignment'] = field(default_factory=list)
    where: Optional[WhereClause] = None


@dataclass
class Assignment(ASTNode):
    """Column assignment (SET col = expr)"""
    column: str
    value: Expression


# ==============================================================================
# UPDATE Statement
# ==============================================================================

@dataclass
class UpdateStatement(Statement):
    """UPDATE statement"""
    with_clause: Optional[WithClause] = None
    conflict_resolution: Optional[ConflictResolution] = None  # OR IGNORE, etc.
    table: QualifiedIdentifier = None
    table_alias: Optional[str] = None
    indexed_by: Optional[str] = None
    not_indexed: bool = False
    assignments: List[Assignment] = field(default_factory=list)
    from_clause: Optional[FromClause] = None  # UPDATE FROM extension
    where: Optional[WhereClause] = None
    order_by: Optional[OrderByClause] = None  # if SQLITE_ENABLE_UPDATE_DELETE_LIMIT
    limit: Optional[LimitClause] = None  # if SQLITE_ENABLE_UPDATE_DELETE_LIMIT
    returning: Optional[ReturningClause] = None


# ==============================================================================
# DELETE Statement
# ==============================================================================

@dataclass
class DeleteStatement(Statement):
    """DELETE statement"""
    with_clause: Optional[WithClause] = None
    table: QualifiedIdentifier = None
    table_alias: Optional[str] = None
    indexed_by: Optional[str] = None
    not_indexed: bool = False
    where: Optional[WhereClause] = None
    order_by: Optional[OrderByClause] = None  # if SQLITE_ENABLE_UPDATE_DELETE_LIMIT
    limit: Optional[LimitClause] = None  # if SQLITE_ENABLE_UPDATE_DELETE_LIMIT
    returning: Optional[ReturningClause] = None


#> ## Data Definition Statements (DDL)
#
# DDL statements define and modify database schema: CREATE, ALTER, DROP.
#
# ### CREATE TABLE
#
# Defines a new table with:
#
# - **Column Definitions**: Name, type, and constraints for each column
# - **Table Constraints**: PRIMARY KEY, UNIQUE, CHECK, FOREIGN KEY across columns
# - **Options**:
#   - WITHOUT ROWID: Use primary key as physical storage key (no hidden rowid)
#   - STRICT: Enforce type affinity strictly (SQLite 3.37+)
#   - IF NOT EXISTS: No error if table already exists
#   - TEMPORARY: Table persists only for the session
#
# #### Column Constraints
#
# - PRIMARY KEY [AUTOINCREMENT]: Unique identifier, auto-increment for INTEGER
# - NOT NULL: Require value
# - UNIQUE: No duplicate values
# - CHECK(expr): Value must satisfy expression
# - DEFAULT expr: Default value if not specified
# - COLLATE: Collation for text comparison
# - REFERENCES: Foreign key to another table
# - GENERATED ALWAYS AS (expr) [STORED|VIRTUAL]: Computed column
#
# #### Table Constraints
#
# Applied after all columns, can reference multiple columns:
# - PRIMARY KEY(col1, col2, ...): Composite primary key
# - UNIQUE(col1, col2, ...): Composite unique constraint
# - CHECK(expr): Table-level check
# - FOREIGN KEY(cols) REFERENCES table(cols): Foreign key relationship

# ==============================================================================
# CREATE TABLE Statement
# ==============================================================================

@dataclass
class CreateTableStatement(Statement):
    """CREATE TABLE statement"""
    temporary: bool = False  # TEMP/TEMPORARY
    if_not_exists: bool = False
    table_name: QualifiedIdentifier = None
    columns: List['ColumnDefinition'] = field(default_factory=list)
    constraints: List['TableConstraint'] = field(default_factory=list)
    without_rowid: bool = False
    strict: bool = False
    as_select: Optional[SelectStatement] = None  # for CREATE TABLE AS SELECT


@dataclass
class ColumnDefinition(ASTNode):
    """Column definition"""
    name: str
    type_name: Optional[str] = None
    constraints: List['ColumnConstraint'] = field(default_factory=list)


@dataclass
class ColumnConstraint(ASTNode):
    """Column constraint"""
    name: Optional[str] = None  # CONSTRAINT name
    constraint_type: str = None  # PRIMARY_KEY, NOT_NULL, UNIQUE, CHECK, DEFAULT, COLLATE, REFERENCES, GENERATED
    # Specific fields based on type
    primary_key: bool = False
    autoincrement: bool = False
    unique: bool = False
    not_null: bool = False
    check_expression: Optional[Expression] = None
    default_value: Optional[Expression] = None
    collation: Optional[str] = None
    foreign_key: Optional['ForeignKeyClause'] = None
    generated: Optional['GeneratedColumnClause'] = None
    on_conflict: Optional[ConflictResolution] = None


@dataclass
class TableConstraint(ASTNode):
    """Table constraint"""
    name: Optional[str] = None  # CONSTRAINT name
    constraint_type: str = None  # PRIMARY_KEY, UNIQUE, CHECK, FOREIGN_KEY
    # Specific fields
    columns: List['IndexedColumn'] = field(default_factory=list)  # for PRIMARY KEY, UNIQUE, FOREIGN KEY
    check_expression: Optional[Expression] = None  # for CHECK
    foreign_key: Optional['ForeignKeyClause'] = None  # for FOREIGN KEY
    on_conflict: Optional[ConflictResolution] = None


@dataclass
class ForeignKeyClause(ASTNode):
    """FOREIGN KEY clause"""
    foreign_table: str
    foreign_columns: List[str] = field(default_factory=list)
    on_delete: Optional[str] = None  # SET NULL, SET DEFAULT, CASCADE, RESTRICT, NO ACTION
    on_update: Optional[str] = None
    match: Optional[str] = None  # MATCH name
    deferrable: Optional[bool] = None
    initially_deferred: Optional[bool] = None


@dataclass
class GeneratedColumnClause(ASTNode):
    """GENERATED ALWAYS AS clause"""
    expression: Expression
    stored: bool = False  # STORED vs VIRTUAL


@dataclass
class IndexedColumn(ASTNode):
    """Indexed column (for indexes and constraints)"""
    expression: Expression  # can be column name or expression
    collation: Optional[str] = None
    direction: Optional[OrderDirection] = None


# ==============================================================================
# ALTER TABLE Statement
# ==============================================================================

@dataclass
class AlterTableStatement(Statement):
    """ALTER TABLE statement"""
    table_name: QualifiedIdentifier = None
    action: 'AlterTableAction' = None


@dataclass
class AlterTableAction(ASTNode):
    """ALTER TABLE action"""
    action_type: str = None  # RENAME_TABLE, RENAME_COLUMN, ADD_COLUMN, DROP_COLUMN
    # Specific fields
    new_table_name: Optional[str] = None  # for RENAME TABLE
    old_column_name: Optional[str] = None  # for RENAME COLUMN
    new_column_name: Optional[str] = None  # for RENAME COLUMN
    column_definition: Optional[ColumnDefinition] = None  # for ADD COLUMN
    column_name: Optional[str] = None  # for DROP COLUMN


# ==============================================================================
# CREATE INDEX Statement
# ==============================================================================

@dataclass
class CreateIndexStatement(Statement):
    """CREATE INDEX statement"""
    unique: bool = False
    if_not_exists: bool = False
    index_name: QualifiedIdentifier = None
    table_name: str = None
    indexed_columns: List[IndexedColumn] = field(default_factory=list)
    where: Optional[WhereClause] = None  # partial index


# ==============================================================================
# CREATE VIEW Statement
# ==============================================================================

@dataclass
class CreateViewStatement(Statement):
    """CREATE VIEW statement"""
    temporary: bool = False
    if_not_exists: bool = False
    view_name: QualifiedIdentifier = None
    columns: List[str] = field(default_factory=list)
    select: SelectStatement = None


# ==============================================================================
# CREATE TRIGGER Statement
# ==============================================================================

@dataclass
class CreateTriggerStatement(Statement):
    """CREATE TRIGGER statement"""
    temporary: bool = False
    if_not_exists: bool = False
    trigger_name: QualifiedIdentifier = None
    timing: Optional[TriggerTiming] = None  # BEFORE, AFTER, or None for INSTEAD OF
    instead_of: bool = False
    event: TriggerEvent = None  # DELETE, INSERT, UPDATE
    update_columns: List[str] = field(default_factory=list)  # for UPDATE OF
    table_name: str = None
    for_each_row: bool = True  # always true in SQLite currently
    when: Optional[WhereClause] = None
    body: List[Statement] = field(default_factory=list)


# ==============================================================================
# CREATE VIRTUAL TABLE Statement
# ==============================================================================

@dataclass
class CreateVirtualTableStatement(Statement):
    """CREATE VIRTUAL TABLE statement"""
    if_not_exists: bool = False
    table_name: QualifiedIdentifier = None
    module_name: str = None
    module_arguments: List[str] = field(default_factory=list)


# ==============================================================================
# DROP Statements
# ==============================================================================

@dataclass
class DropTableStatement(Statement):
    """DROP TABLE statement"""
    if_exists: bool = False
    table_name: QualifiedIdentifier = None


@dataclass
class DropIndexStatement(Statement):
    """DROP INDEX statement"""
    if_exists: bool = False
    index_name: QualifiedIdentifier = None


@dataclass
class DropViewStatement(Statement):
    """DROP VIEW statement"""
    if_exists: bool = False
    view_name: QualifiedIdentifier = None


@dataclass
class DropTriggerStatement(Statement):
    """DROP TRIGGER statement"""
    if_exists: bool = False
    trigger_name: QualifiedIdentifier = None


# ==============================================================================
# Transaction Control Statements
# ==============================================================================

@dataclass
class BeginStatement(Statement):
    """BEGIN TRANSACTION statement"""
    transaction_type: Optional[TransactionType] = None


@dataclass
class CommitStatement(Statement):
    """COMMIT TRANSACTION statement"""
    pass


@dataclass
class RollbackStatement(Statement):
    """ROLLBACK TRANSACTION statement"""
    savepoint: Optional[str] = None  # TO SAVEPOINT name


@dataclass
class SavepointStatement(Statement):
    """SAVEPOINT statement"""
    name: str


@dataclass
class ReleaseStatement(Statement):
    """RELEASE SAVEPOINT statement"""
    name: str


# ==============================================================================
# Database Management Statements
# ==============================================================================

@dataclass
class AttachStatement(Statement):
    """ATTACH DATABASE statement"""
    database_expression: Expression
    schema_name: str


@dataclass
class DetachStatement(Statement):
    """DETACH DATABASE statement"""
    schema_name: str


@dataclass
class AnalyzeStatement(Statement):
    """ANALYZE statement"""
    target: Optional[QualifiedIdentifier] = None  # schema, table, or index


@dataclass
class VacuumStatement(Statement):
    """VACUUM statement"""
    schema_name: Optional[str] = None
    into_filename: Optional[Expression] = None


@dataclass
class ReindexStatement(Statement):
    """REINDEX statement"""
    target: Optional[Union[str, QualifiedIdentifier]] = None  # collation, table, or index


@dataclass
class ExplainStatement(Statement):
    """EXPLAIN [QUERY PLAN] statement"""
    query_plan: bool = False
    statement: Statement = None


@dataclass
class PragmaStatement(Statement):
    """PRAGMA statement"""
    pragma_name: str
    schema_name: Optional[str] = None
    value: Optional[Union[str, int, Expression]] = None
