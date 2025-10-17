# SQLite Complete Syntax Reference

*Comprehensive reference documentation for SQLite SQL syntax, scraped from https://sqlite.org/lang.html*

---

## Table of Contents

1. [Data Types and Storage](#data-types-and-storage)
2. [SQL Statements](#sql-statements)
   - [SELECT](#select-statement)
   - [INSERT](#insert-statement)
   - [UPDATE](#update-statement)
   - [DELETE](#delete-statement)
   - [CREATE TABLE](#create-table)
   - [ALTER TABLE](#alter-table)
   - [CREATE INDEX](#create-index)
   - [CREATE VIEW](#create-view)
   - [CREATE TRIGGER](#create-trigger)
   - [CREATE VIRTUAL TABLE](#create-virtual-table)
   - [DROP Statements](#drop-statements)
3. [Transaction Control](#transaction-control)
4. [Database Management](#database-management)
5. [Expressions](#expressions)
6. [Clauses and Keywords](#clauses-and-keywords)
7. [Functions](#functions)
8. [Keywords and Reserved Words](#keywords-and-reserved-words)
9. [Comments](#comments)

---

## Data Types and Storage

### Storage Classes

SQLite supports five fundamental storage classes:

- **NULL**: Null values
- **INTEGER**: Signed integers stored in 0-8 bytes depending on magnitude
- **REAL**: 8-byte IEEE floating point numbers
- **TEXT**: Text strings in UTF-8, UTF-16BE, or UTF-16LE encoding
- **BLOB**: Binary data stored exactly as input

### Dynamic Typing

Unlike most SQL databases using rigid typing, SQLite employs a "dynamic type system" where "the datatype of a value is associated with the value itself, not with its container." This allows flexibility while maintaining backward compatibility with statically-typed databases.

### Type Affinity

Type affinity represents the *recommended* (not required) storage class for a column. SQLite recognizes five affinity types:

- **TEXT**: Stores NULL, TEXT, or BLOB; converts numeric data to text
- **NUMERIC**: Accepts all five storage classes; converts well-formed text integers/reals to numeric types
- **INTEGER**: Behaves like NUMERIC (differs only in CAST expressions)
- **REAL**: Forces integer values into floating-point representation
- **BLOB**: No preference; no coercion attempted

#### Determining Column Affinity

Affinity is determined by checking the declared type string in this order:

1. Contains "INT" → INTEGER affinity
2. Contains "CHAR", "CLOB", or "TEXT" → TEXT affinity
3. Contains "BLOB" or no type specified → BLOB affinity
4. Contains "REAL", "FLOA", or "DOUB" → REAL affinity
5. Otherwise → NUMERIC affinity

### Type Conversions in Comparisons

Before comparison, SQLite applies affinity conversions:

- If one operand has INTEGER/REAL/NUMERIC affinity and the other has TEXT/BLOB/no affinity, NUMERIC affinity applies to the latter
- If one has TEXT affinity and the other has no affinity, TEXT affinity applies
- Otherwise, no conversion occurs

### Special Data Types

**Boolean**: Stored as integers (0 = false, 1 = true); keywords TRUE/FALSE are supported

---

## SQL Statements

### SELECT Statement

The SELECT statement queries databases, returning zero or more rows with a fixed number of columns per row without modifying data.

#### Core Processing Steps

Simple SELECT statements follow a four-step process:

1. **FROM clause processing**: Determines input data from tables or subqueries
2. **WHERE clause filtering**: Removes rows not matching the boolean expression
3. **Result row generation**: Computes output through aggregation or direct evaluation
4. **DISTINCT processing**: Removes duplicate rows if specified

#### Basic Syntax

```sql
SELECT [DISTINCT|ALL] result-column
FROM table
WHERE expr
GROUP BY expr
HAVING expr
ORDER BY expr
LIMIT expr
```

#### FROM Clause

- Accepts single or multiple tables/subqueries
- Supports various JOIN types: INNER, LEFT, RIGHT, FULL, CROSS, NATURAL
- Joins use cartesian products with optional ON/USING constraints

#### WHERE Clause

- Filters input data using boolean expressions
- Excludes rows evaluating to false or NULL
- For outer joins, applied after ON clause processing

#### Aggregation

- **Non-aggregate queries**: Evaluate expressions per input row
- **Aggregate without GROUP BY**: Single output row with aggregate functions evaluated across entire dataset
- **Aggregate with GROUP BY**: Groups rows by expression values, one output row per group

#### DISTINCT Processing

Removes duplicates using "IS DISTINCT FROM" operator, treating NULL values as equal.

#### Compound SELECT Statements

Multiple simple SELECTs combine using UNION, UNION ALL, INTERSECT, or EXCEPT operators. All constituent queries must return identical column counts.

#### ORDER BY Clause

Sorts results by specified expressions. Supports:
- Integer column references (1-based indexing)
- Column aliases
- ASC/DESC keywords (ascending default)
- NULLS FIRST/NULLS LAST modifiers

#### LIMIT and OFFSET

- LIMIT restricts row count
- OFFSET skips initial rows
- Both accept scalar expressions converting to integers

---

### INSERT Statement

The INSERT statement adds new rows to an existing table in SQLite.

#### Form 1: INSERT INTO with VALUES

```sql
INSERT INTO table [(column-list)] VALUES (value-list)
```

"The first form (with the 'VALUES' keyword) creates one or more new rows in an existing table."

When column names are omitted, the number of values must match the table's column count. When specified, values populate corresponding named columns, with unlisted columns receiving default values or NULL.

#### Form 2: INSERT INTO with SELECT

```sql
INSERT INTO table [(column-list)] SELECT ...
```

"The second form of the INSERT statement contains a SELECT statement instead of a VALUES clause."

This approach inserts rows derived from a SELECT query result. The column count in the SELECT result must match either the specified column list or the table's total columns. Complex SELECT statements with ORDER BY and LIMIT clauses are permitted.

An important parsing note: "the SELECT statement should always contain a WHERE clause...if the upsert-clause is present" to avoid ambiguity with JOIN constraints.

#### Form 3: INSERT INTO with DEFAULT VALUES

```sql
INSERT INTO table DEFAULT VALUES
```

"The INSERT ... DEFAULT VALUES statement inserts a single new row into the named table."

Each column receives its defined default value or NULL. This form does not support upsert clauses.

#### Conflict Resolution

The INSERT keyword can be replaced with REPLACE or "INSERT OR _action_" to specify alternative conflict resolution strategies. SQLite supports ROLLBACK, ABORT, FAIL, IGNORE, and REPLACE options.

#### Additional Features

- Optional schema-name prefix (top-level statements only)
- Table alias support via "AS alias" for use in WHERE and SET clauses
- UPSERT clause support for conditional UPDATE behavior on constraint violations

---

### UPDATE Statement

The UPDATE statement modifies values in database table rows. "An UPDATE statement is used to modify a subset of the values stored in zero or more rows of the database table."

#### Basic Syntax

```sql
UPDATE [OR conflict-resolution] table-name
SET column = expr [, column = expr ...]
[WHERE expr]
[FROM other-tables]
[RETURNING result-columns]
```

The fundamental structure includes:
- Optional WITH clause for common table expressions
- UPDATE keyword with optional conflict resolution (OR ROLLBACK, OR REPLACE, OR IGNORE, OR FAIL, OR ABORT)
- Target table name
- SET clause with column assignments
- Optional WHERE clause
- Optional FROM clause
- Optional RETURNING clause

#### Key Behaviors

**Row Selection**: Without a WHERE clause, all rows are modified. The WHERE clause filters which rows receive updates. It's valid if no rows match the condition.

**Column Assignment**: The SET clause specifies which columns change and their new values. "If a single column-name appears more than once in the list of assignment expressions, all but the rightmost occurrence is ignored."

**Expression Evaluation**: All expressions in SET clauses evaluate before any modifications occur, allowing references to current column values.

#### UPDATE FROM Extension

Available since version 3.33.0, this feature allows joining the target table with other tables to determine updates. The documentation notes this "is an extension to SQL that allows an UPDATE statement to be driven by other tables."

Example use case: adjusting inventory based on aggregated daily sales data through a subquery join.

#### Trigger Restrictions

Within CREATE TRIGGER bodies:
- Table names must be unqualified (no schema prefix)
- INDEXED BY and NOT INDEXED clauses prohibited
- LIMIT and ORDER BY clauses unsupported

#### Optional LIMIT and ORDER BY

When compiled with SQLITE_ENABLE_UPDATE_DELETE_LIMIT, UPDATE statements support:
- ORDER BY for sorting candidate rows
- LIMIT for restricting update count
- OFFSET for skipping initial rows

"The ORDER BY clause on an UPDATE statement is used only to determine which rows fall within the LIMIT."

---

### DELETE Statement

The DELETE command removes records from a specified table. "If the WHERE clause is not present, all records in the table are deleted."

#### Basic Syntax

```sql
DELETE FROM table-name
[WHERE expr]
[RETURNING result-columns]
```

The fundamental structure includes:
- `DELETE FROM qualified-table-name`
- Optional WHERE clause for conditional deletion
- Optional RETURNING clause to retrieve deleted row data
- Support for Common Table Expressions (CTEs)

#### Key Behaviors

When a WHERE clause is included, only rows matching the boolean expression are removed, while rows evaluating to false or NULL are retained.

#### Trigger Restrictions

DELETE statements within trigger bodies have specific limitations:

- Table names must be unqualified (no schema prefix allowed)
- INDEXED BY and NOT INDEXED clauses are prohibited
- LIMIT and ORDER BY clauses cannot be used
- RETURNING clauses are unsupported

#### Optional LIMIT and ORDER BY

When compiled with `SQLITE_ENABLE_UPDATE_DELETE_LIMIT`, DELETE supports:

- **LIMIT clause**: Restricts the maximum number of rows deleted
- **OFFSET clause**: Skips rows before deletion begins
- **ORDER BY clause**: Determines which rows fall within the LIMIT range (does not affect deletion order)

#### Truncate Optimization

SQLite automatically optimizes DELETE operations when both WHERE and RETURNING clauses are absent and the table has no triggers. This "truncate" optimization significantly improves performance by erasing entire table contents without visiting individual rows. The optimization can be disabled via compile-time switches or runtime authorizer callbacks.

---

### CREATE TABLE

The CREATE TABLE command establishes new tables in SQLite databases. It specifies "the name of the new table," "the name of each column," and "the declared type of each column."

#### Basic Syntax

```sql
CREATE [TEMP|TEMPORARY] TABLE [IF NOT EXISTS] [schema-name.]table-name (
    column-name type [column-constraint ...],
    ...
    [table-constraint ...]
) [table-options]
```

#### Core Syntax Structure

The basic syntax includes:
- Table name and optional schema specification
- Column definitions with optional constraints
- Table-level constraints
- Options like WITHOUT ROWID or STRICT

#### Column Definitions

**Column Definitions** can include:
- Data type declarations
- DEFAULT values (constants, expressions, or special keywords like CURRENT_TIMESTAMP)
- COLLATE clauses for collation sequences
- Generated column specifications
- Constraints (PRIMARY KEY, UNIQUE, CHECK, NOT NULL, FOREIGN KEY)

#### Table Constraints

**Table Constraints** allow:
- Primary keys (single or composite columns)
- Unique constraints (multiple per table)
- Check constraints with expressions
- Foreign key relationships

#### Special Considerations

**INTEGER PRIMARY KEY**: When a column is declared as INTEGER PRIMARY KEY, it becomes an alias for the internal rowid, enabling optimized retrieval and sorting operations.

**CREATE TABLE AS SELECT**: This variant creates and populates tables from query results, automatically determining column types based on "expression affinity" of result columns.

```sql
CREATE TABLE table-name AS SELECT ...
```

**Constraint Enforcement**: "Constraints are checked during INSERT and UPDATE" but queries and DELETE statements typically don't verify constraints.

**WITHOUT ROWID Tables**: Available in SQLite 3.8.2+, these tables omit the implicit rowid structure.

```sql
CREATE TABLE table-name (...) WITHOUT ROWID
```

---

### ALTER TABLE

SQLite supports a limited subset of ALTER TABLE operations. "The ALTER TABLE command in SQLite allows these alterations of an existing table: it can be renamed; a column can be renamed; a column can be added to it; or a column can be dropped from it."

#### Supported Operations

##### 1. RENAME TABLE

```sql
ALTER TABLE table-name RENAME TO new-table-name
```

Changes a table's name within the same database. The command preserves attached triggers and indices. As of version 3.25.0, references within trigger bodies and view definitions are also updated automatically.

##### 2. RENAME COLUMN

```sql
ALTER TABLE table-name RENAME COLUMN old-name TO new-name
```

Modifies a column name throughout the table definition and all associated indexes, triggers, and views. The operation fails if it creates semantic ambiguity in dependent objects.

##### 3. ADD COLUMN

```sql
ALTER TABLE table-name ADD COLUMN column-definition
```

Appends new columns to existing tables with these restrictions:
- Cannot include PRIMARY KEY or UNIQUE constraints
- Cannot use CURRENT_TIME, CURRENT_DATE, CURRENT_TIMESTAMP, or parenthesized expressions as defaults
- NOT NULL columns require non-NULL defaults
- Foreign key columns with REFERENCES clauses need NULL defaults when constraints are enabled
- Cannot be STORED generated columns (VIRTUAL allowed)

##### 4. DROP COLUMN

```sql
ALTER TABLE table-name DROP COLUMN column-name
```

Removes columns that meet these criteria:
- Not a PRIMARY KEY or part of one
- No UNIQUE constraint
- Not indexed
- Not referenced in partial indexes, CHECK constraints, foreign keys, generated columns, triggers, or views

#### Performance Characteristics

Simple operations (renames, unconstrained additions) modify only schema text and execute independently of table size. Operations involving constraint validation or column deletion require reading/writing all existing data, making execution time proportional to table content volume.

#### Schema Modification Approach

SQLite stores schemas as plain text in the `sqlite_schema` table. ALTER TABLE modifies this text and reparses the entire schema, succeeding only if the result remains valid.

---

### CREATE INDEX

The CREATE INDEX command establishes a new index on a previously created table. "The CREATE INDEX command consists of the keywords 'CREATE INDEX' followed by the name of the new index, the keyword 'ON', the name of a previously created table."

#### Basic Syntax

```sql
CREATE [UNIQUE] INDEX [IF NOT EXISTS] [schema-name.]index-name
ON table-name (indexed-column [, indexed-column ...])
[WHERE expr]
```

The command requires:
- Keywords: CREATE INDEX
- Index name
- Table name (preceded by ON keyword)
- Parenthesized list of column names and/or expressions for the index key
- Optional WHERE clause for partial indexes

#### Key Features

**IF NOT EXISTS Clause**
When included, this clause prevents errors if an index with that name already exists, making the command a no-op in such cases.

**Unique Indexes**
The UNIQUE keyword prevents duplicate entries. Notably, "all NULL values are considered different from all other NULL values and are thus unique," which aligns with PostgreSQL, MySQL, and Oracle's interpretation.

**Expression-Based Indexes**
Indexes can use expressions, but with restrictions: they cannot reference other tables, use subqueries, or employ functions with variable results like random(). Expression indexes require SQLite version 3.9.0 or later.

**Sort Order**
Columns can be followed by ASC or DESC keywords. Support depends on schema format version—legacy format (1) ignores sort order, while descending index format (4) respects it.

**Collations**
The COLLATE clause specifies text collating sequences, defaulting to the column's defined sequence or BINARY if undefined.

---

### CREATE VIEW

The CREATE VIEW statement assigns a name to a pre-packaged SELECT statement.

#### Syntax

```sql
CREATE [TEMP|TEMPORARY] VIEW [IF NOT EXISTS] [schema-name.]view-name [(column-list)]
AS select-stmt
```

The basic structure includes:

- **CREATE [TEMP|TEMPORARY] VIEW [IF NOT EXISTS]** schema-name.view-name
- **Optional column-name list** for explicit column naming
- **AS select-stmt** containing the query definition

#### Key Characteristics

**Scope and Visibility:**
"If the TEMP or TEMPORARY keyword occurs in between CREATE and VIEW then the view that is created is only visible to the database connection that created it and is automatically deleted when the database connection is closed."

**Read-Only Nature:**
"You cannot DELETE, INSERT, or UPDATE a view. Views are read-only in SQLite." However, INSTEAD OF triggers can provide workaround functionality for modifications.

**Column Naming:**
The documentation recommends explicitly listing column names following the view name. When omitted, column names derive from the SELECT statement's result set. The column-name list syntax was introduced in SQLite 3.9.0 (2015-10-14).

**Removal:**
Views are removed using the DROP VIEW command.

#### Schema Placement

Views are created in the main database by default, or in a specified schema. Combining schema-name with TEMP is an error unless the schema is "temp".

---

### CREATE TRIGGER

The CREATE TRIGGER statement adds automated database operations to the schema.

#### Syntax

```sql
CREATE [TEMP|TEMPORARY] TRIGGER [IF NOT EXISTS] [schema-name.]trigger-name
[BEFORE|AFTER|INSTEAD OF] [DELETE|INSERT|UPDATE [OF column-list]] ON table-name
[FOR EACH ROW]
[WHEN expr]
BEGIN
    sql-statements;
END
```

The basic structure allows specification of:

- **Timing**: BEFORE or AFTER (BEFORE is default)
- **Event**: DELETE, INSERT, or UPDATE
- **Scope**: FOR EACH ROW (currently the only supported option)
- **Condition**: Optional WHEN clause
- **Actions**: SQL statements executed when trigger fires

#### Key Characteristics

**Trigger Firing**: Triggers execute once per affected row. For UPDATE operations, you can specify particular columns using "UPDATE OF column-name" syntax to limit when the trigger activates.

**Row References**: Within trigger bodies, use NEW and OLD prefixes to access column values:
- INSERT triggers: NEW references only
- UPDATE triggers: both NEW and OLD available
- DELETE triggers: OLD references only

**Conditional Execution**: A WHEN clause restricts trigger execution to specific conditions. Without it, the trigger fires every time.

#### Trigger Types

**BEFORE/AFTER Triggers**: Work exclusively on regular tables. BEFORE triggers execute before the triggering operation; AFTER triggers execute afterward.

**INSTEAD OF Triggers**: Function only on views. Rather than performing the original operation, the trigger's statements execute instead. This enables write operations on views.

#### Restrictions Within Triggers

Statements inside triggers face limitations:
- Table names must be unqualified (no schema prefix)
- "INSERT INTO table DEFAULT VALUES" syntax is unsupported
- INDEXED BY and NOT INDEXED clauses prohibited
- ORDER BY and LIMIT clauses not permitted
- Common table expressions require embedding in subqueries

#### RAISE() Function

The RAISE() function enables error handling within triggers:

- "RAISE(ROLLBACK, message)" rolls back and terminates with SQLITE_CONSTRAINT error
- "RAISE(ABORT, message)" and "RAISE(FAIL, message)" perform similar operations
- "RAISE(IGNORE)" abandons remaining trigger execution without rolling back changes

#### Practical Example

A trigger maintaining referential integrity across tables:

```sql
CREATE TRIGGER update_customer_address UPDATE OF address ON customers
  BEGIN
    UPDATE orders SET address = new.address
    WHERE customer_name = old.name;
  END
```

---

### CREATE VIRTUAL TABLE

A virtual table functions as an interface to external storage or computation systems, appearing as a standard table without storing data directly in the database file.

#### Syntax

```sql
CREATE VIRTUAL TABLE [IF NOT EXISTS] [schema-name.]table-name
USING module-name [(module-argument, ...)]
```

#### Key Characteristics

**Capabilities:** Virtual tables support most operations available for regular tables, with notable exceptions:
- Cannot create indices on virtual tables
- Cannot create triggers on virtual tables
- Some implementations may impose additional restrictions (many are read-only)

#### Module Requirements

The module-name references an object implementing the virtual table functionality. Before executing a CREATE VIRTUAL TABLE statement, the module must be registered with the SQLite database connection using either `sqlite3_create_module()` or `sqlite3_create_module_v2()`.

#### Arguments

Modules accept zero or more comma-separated arguments with balanced parentheses. The syntax is flexible enough to resemble column definitions from traditional CREATE TABLE statements. SQLite passes arguments directly to the `xCreate` and `xConnect` methods without interpretation—the module implementation handles parsing and interpretation.

#### Removal

Virtual tables are destroyed using the standard `DROP TABLE` statement. No separate DROP VIRTUAL TABLE command exists.

---

### DROP Statements

#### DROP TABLE

```sql
DROP TABLE [IF EXISTS] [schema-name.]table-name
```

Removes a table from the database schema. If IF EXISTS is specified, no error occurs if the table doesn't exist.

#### DROP INDEX

```sql
DROP INDEX [IF EXISTS] [schema-name.]index-name
```

Removes an index from the database schema.

#### DROP VIEW

```sql
DROP VIEW [IF EXISTS] [schema-name.]view-name
```

Removes a view from the database schema.

#### DROP TRIGGER

```sql
DROP TRIGGER [IF EXISTS] [schema-name.]trigger-name
```

Removes a trigger from the database schema.

---

## Transaction Control

### BEGIN TRANSACTION

Initiates transactions with optional modifiers.

#### Syntax

```sql
BEGIN [DEFERRED|IMMEDIATE|EXCLUSIVE] [TRANSACTION]
```

#### Core Transaction Concepts

##### Automatic vs. Manual Transactions

"No reads or writes occur except within a transaction." Database operations automatically initiate transactions if none exist, committing when the final statement completes. Manual transactions begin with BEGIN and persist until explicit COMMIT or ROLLBACK commands execute.

##### Read vs. Write Transactions

SQLite permits multiple simultaneous read transactions across connections but allows only one active write transaction. Read operations trigger read transactions; CREATE, DELETE, DROP, INSERT, and UPDATE statements initiate write transactions. The system can upgrade read transactions to write transactions when needed, though this fails with SQLITE_BUSY if another connection is already writing.

##### Transaction Types

**DEFERRED** (default): Delays actual transaction start until first database access. A SELECT begins a read transaction; write statements upgrade to write transactions.

**IMMEDIATE**: Starts write transactions immediately without awaiting write statements, potentially failing with SQLITE_BUSY.

**EXCLUSIVE**: Similar to IMMEDIATE but prevents other connections from reading during the transaction in non-WAL journaling modes.

---

### COMMIT TRANSACTION

Finalizes transactions using COMMIT, TRANSACTION, or END keywords.

#### Syntax

```sql
COMMIT [TRANSACTION]
END [TRANSACTION]
```

Both COMMIT and END are equivalent and finalize the current transaction, making all changes permanent.

---

### ROLLBACK TRANSACTION

Reverts changes, optionally targeting specific savepoints.

#### Syntax

```sql
ROLLBACK [TRANSACTION] [TO [SAVEPOINT] savepoint-name]
```

Undoes all changes made in the current transaction. If TO SAVEPOINT is specified, only rolls back to that savepoint.

#### Error Handling

Certain errors (SQLITE_FULL, SQLITE_IOERR, SQLITE_BUSY, SQLITE_NOMEM) may trigger automatic rollbacks. The documentation recommends explicitly issuing ROLLBACK commands in response to these errors.

---

### SAVEPOINT

Savepoints function as "a method of creating transactions, similar to BEGIN and COMMIT, except that the SAVEPOINT and RELEASE commands are named and may be nested."

#### Syntax

```sql
SAVEPOINT savepoint-name
```

The SAVEPOINT instruction initiates a named transaction that can be nested within or outside existing transactions. When a SAVEPOINT operates as the outermost transaction outside a BEGIN...COMMIT block, it behaves identically to BEGIN DEFERRED TRANSACTION.

---

### RELEASE SAVEPOINT

RELEASE operates analogously to COMMIT but specifically for savepoints.

#### Syntax

```sql
RELEASE [SAVEPOINT] savepoint-name
```

The instruction "causes all savepoints back to and including the most recent savepoint with a matching name to be removed from the transaction stack."

Key characteristics:
- Releasing inner transactions doesn't write changes to disk immediately
- Only the outermost RELEASE triggers actual database commitment
- If the savepoint name doesn't match any current savepoint, the command fails and returns an error
- Inner transaction changes can still be undone by outer transaction rollbacks

---

## Database Management

### ATTACH DATABASE

The ATTACH DATABASE statement extends a database connection by adding another database file. "It adds another database file to the current database connection."

#### Syntax

```sql
ATTACH DATABASE expr AS schema-name
```

#### Key Details

**File Specification:**
The expression before AS identifies the database file using the same semantics as `sqlite3_open()`. Special values include ":memory:" for in-memory databases and an empty string for temporary databases. URI filenames are supported if enabled on the connection.

**Schema Naming:**
The identifier following AS becomes the internal schema name within SQLite. "'main' and 'temp' refer to the main database and the database used for temporary tables" and cannot be attached or detached.

**Table References:**
Tables in attached databases use the format `schema-name.table-name`. If a table name is unique across all databases, the schema prefix is optional. When naming conflicts exist, "the table chosen is the one in the database that was least recently attached."

**Transaction Behavior:**
Multi-database transactions remain atomic under standard conditions, but atomicity is limited to individual files when the main database is ":memory:" or journal_mode is WAL.

**Connection Limits:**
The maximum number of simultaneously attached databases is configurable via `sqlite3_limit()` with the `SQLITE_LIMIT_ATTACHED` parameter.

---

### DETACH DATABASE

The DETACH statement removes a database connection that was previously established using the ATTACH statement.

#### Syntax

```sql
DETACH [DATABASE] schema-name
```

"This command detaches an additional database connection previously attached using the ATTACH statement."

#### Behavior by Mode

**Non-shared cache mode:** You can attach the same database file multiple times under different names. Detaching one connection leaves the others active.

**Shared cache mode:** The system prevents attaching identical database files more than once, raising an error if attempted.

---

### ANALYZE

The ANALYZE command collects statistics about tables and indices, storing them in internal database tables. The query optimizer uses this information to make better query planning decisions.

#### Syntax

```sql
ANALYZE [schema-name.table-or-index-name | schema-name | table-name | index-name]
```

When invoked without arguments, ANALYZE processes the main database and all attached databases. Specifying a schema name analyzes all tables and indices in that schema. A table name analyzes only that table and its associated indices. An index name analyzes only that specific index.

#### Key Recommendations

**Using PRAGMA optimize (Preferred Method):**
"The PRAGMA optimize command will automatically run ANALYZE when needed." Suggested approaches include:

- Short-lived connections: Execute "PRAGMA optimize;" before closing
- Long-lived connections: Run "PRAGMA optimize=0x10002;" on initial connection, then periodically thereafter
- After schema changes: Always run after CREATE INDEX statements

**Fixed Query Plans:**
For applications requiring consistent query plans across deployments, developers should run ANALYZE during development only, then capture and reuse the resulting statistics table data rather than running ANALYZE in production.

#### Statistics Storage

The system stores statistics in internal tables:
- **sqlite_stat1**: Default statistics table
- **sqlite_stat4**: Additional histogram data (when compiled with SQLITE_ENABLE_STAT4)

These tables can be queried with SELECT and modified with DELETE, INSERT, or UPDATE commands, though manual modifications should be avoided.

#### Approximate ANALYZE

For large databases, "PRAGMA analysis_limit=N" (where N ranges from 100-1000) accelerates ANALYZE by limiting row scans. "An analysis limit of N will strive to limit the number of rows visited in each index to approximately N."

**Limitation**: The sqlite_stat4 table cannot be computed with analysis limits active.

---

### VACUUM

The VACUUM command rebuilds the database file, compacting it to use minimal disk space.

#### Syntax

```sql
VACUUM [schema-name]
VACUUM [schema-name] INTO filename
```

"It rebuilds the database file, repacking it into a minimal amount of disk space."

#### Primary Use Cases

**Space Reclamation**: When data is deleted without auto_vacuum enabled, empty pages remain. VACUUM reclaims this wasted space and reduces file size.

**Defragmentation**: Frequent modifications can scatter table and index data throughout the file. VACUUM consolidates this data contiguously, potentially reducing partially filled pages.

**Security**: "When content is deleted from an SQLite database, the content is not usually erased." VACUUM removes traces of deleted content, preventing forensic recovery—an alternative to `PRAGMA secure_delete=ON`.

**Configuration Changes**: Outside write-ahead log mode, VACUUM allows modification of page_size and auto_vacuum properties after database creation.

#### VACUUM INTO Clause

This variant creates a new vacuumed database in a specified file without modifying the original. The filename can be any SQL expression evaluating to a string, including URI filenames if enabled. The target file must not exist or must be empty.

#### Technical Details

VACUUM works by "copying the contents of the database into a temporary database file and then overwriting the original." This process requires free disk space equal to approximately twice the original database size.

**Important limitation**: VACUUM may alter ROWIDs in tables lacking explicit INTEGER PRIMARY KEY, and fails if open transactions exist on the connection.

---

### REINDEX

"The REINDEX command is used to delete and recreate indices from scratch."

#### Syntax

```sql
REINDEX [collation-name | schema-name.index-name | schema-name.table-name]
```

This proves particularly valuable when collation sequence definitions have been modified or when indexes reference functions whose implementations have changed.

#### Behavior Variations

**No arguments:** Rebuilds all indices across all attached databases.

**Collation-sequence name:** Recreates all indices using that specific collation sequence throughout all attached databases.

**Table identifier:** Rebuilds every index associated with the designated table.

**Index identifier:** Recreates only that particular index.

#### Disambiguation Note

When using the format "REINDEX _name_", the system prioritizes matching against collation names before considering index or table names. To eliminate this ambiguity, always include the schema-name prefix when targeting a specific table or index for reindexing.

---

### EXPLAIN

The EXPLAIN command precedes SQL statements and provides information about query execution.

#### Syntax

```sql
EXPLAIN [sql-stmt]
EXPLAIN QUERY PLAN [sql-stmt]
```

Supported statement types include SELECT, INSERT, UPDATE, DELETE, CREATE TABLE/INDEX/VIEW, DROP, ALTER TABLE, PRAGMA, and many others.

#### Purpose

"Either modification causes the SQL statement to behave as a query and to return information about how the SQL statement would have operated if the EXPLAIN keyword or phrase had been omitted."

#### Key Distinctions

**EXPLAIN alone** returns "the sequence of virtual machine instructions it would have used to execute the command."

**EXPLAIN QUERY PLAN** provides "high-level information regarding the query plan that would have been used."

#### Important Limitations

"The output from EXPLAIN and EXPLAIN QUERY PLAN is intended for interactive analysis and troubleshooting only." It explicitly warns that "Applications should not use EXPLAIN or EXPLAIN QUERY PLAN since their exact behavior is variable and only partially documented."

#### Runtime Behavior

EXPLAIN operates during statement execution via `sqlite3_step()`, not during preparation. This means certain PRAGMA statements and authorizer callbacks execute normally regardless of the EXPLAIN prefix.

---

## Expressions

SQLite expressions form the foundation of SQL queries, supporting literals, operators, functions, and subqueries.

### Core Expression Components

#### Literal Values

SQLite recognizes numeric literals (integers and floats), string constants in single quotes, BLOB literals (hexadecimal prefixed with X), and NULL tokens. "A numeric literal has a decimal point or an exponentiation clause or if it is less than -9223372036854775808 or greater than 9223372036854775807, then it is a floating point literal."

#### Parameters

Placeholders enable runtime value binding through multiple formats:
- `?NNN` for numbered parameters
- `?` for auto-numbered parameters
- `:AAAA`, `@AAAA`, `$AAAA` for named parameters

### Operator Precedence

SQLite implements operators in strict precedence order from highest to lowest:

1. Unary operators: `~`, `+`, `-`
2. COLLATE clause
3. Concatenation and extraction: `||`, `->`, `->>`
4. Arithmetic: `*`, `/`, `%`, `+`, `-`
5. Bitwise: `&`, `|`, `<<`, `>>`
6. Comparison: `<`, `>`, `<=`, `>=`, `=`, `==`, `<>`, `!=`
7. Pattern matching: BETWEEN, IN, LIKE, GLOB, MATCH, REGEXP
8. Logical: NOT, AND, OR

### Pattern Matching Operators

#### LIKE

```sql
expr LIKE pattern [ESCAPE escape-char]
```

"A percent symbol ('%') in the LIKE pattern matches any sequence of zero or more characters in the string. An underscore ('_') in the LIKE pattern matches any single character." Case-insensitive for ASCII by default; the optional ESCAPE clause allows literal wildcard matching.

#### GLOB

```sql
expr GLOB pattern
```

Unix file globbing syntax; case-sensitive unlike LIKE.

#### REGEXP/MATCH

```sql
expr REGEXP pattern
expr MATCH pattern
```

User-defined function syntax requiring application-defined implementations.

### Conditional Expressions

#### CASE

```sql
CASE [expr]
    WHEN condition THEN result
    [WHEN condition THEN result ...]
    [ELSE result]
END
```

Two forms exist—with or without base expressions. The result is the evaluation of the THEN expression for the first matching WHEN condition.

#### COALESCE

```sql
COALESCE(expr1, expr2, ...)
```

Returns the first non-NULL expression.

#### IFNULL

```sql
IFNULL(expr1, expr2)
```

Returns expr1 if not NULL, otherwise returns expr2.

#### NULLIF

```sql
NULLIF(expr1, expr2)
```

Returns NULL if expr1 equals expr2, otherwise returns expr1.

---

## Clauses and Keywords

### WITH Clause (Common Table Expressions)

The WITH clause enables temporary views that exist only during a single SQL statement's execution. SQLite supports two CTE types: ordinary and recursive.

#### Syntax

```sql
WITH [RECURSIVE] cte-name [(column-list)] AS (select-stmt)
[, cte-name [(column-list)] AS (select-stmt) ...]
main-query
```

"Common Table Expressions or CTEs act like temporary views that exist only for the duration of a single SQL statement."

#### Ordinary Common Table Expressions

Ordinary CTEs function as temporary views, helping developers factor out subqueries to improve readability. A WITH clause can contain ordinary CTEs even when the RECURSIVE keyword is present—the keyword doesn't mandate recursion.

#### Recursive Common Table Expressions

Recursive CTEs enable tree and graph traversal queries. Key requirements include:

- The select statement must be a compound select (multiple SELECT statements separated by UNION, UNION ALL, INTERSECT, or EXCEPT)
- One or more individual SELECT statements must reference the CTE table exactly once in their FROM clause
- Non-recursive SELECT statements must precede recursive ones
- Recursive statements cannot use aggregate or window functions

The documentation explains the algorithm: "Run the initial-select and add the results to a queue. While the queue is not empty: Extract a single row from the queue. Insert that single row into the recursive table. Pretend that the single row just extracted is the only row in the recursive table and run the recursive-select, adding all results to the queue."

#### Practical Examples

**Integer sequence generation:**
```sql
WITH RECURSIVE cnt(x) AS (
  VALUES(1) UNION ALL SELECT x+1 FROM cnt WHERE x<1000000
)
SELECT x FROM cnt;
```

**Hierarchical queries** traverse organizational structures or family trees by following parent-child relationships.

**Graph queries** find connected nodes using multiple UNION statements to follow edges in different directions.

#### Materialization Hints

SQLite supports PostgreSQL-compatible hints:
- **MATERIALIZED**: Forces creation of an ephemeral table, preventing query optimization
- **NOT MATERIALIZED**: Treats the CTE like a standard subquery, allowing optimizations

The documentation recommends: "Do not use the MATERIALIZED or NOT MATERIALIZED keywords on a common table expression unless you have a compelling reason to do so."

---

### RETURNING Clause

The RETURNING clause is an optional addition to DELETE, INSERT, and UPDATE statements that "causes the statement to return one result row for each database row that is deleted, inserted, or updated."

#### Syntax

```sql
[DELETE|INSERT|UPDATE statement] RETURNING result-column [, result-column ...]
```

This SQLite extension, modeled after PostgreSQL, has been available since version 3.35.0 (March 2021).

The clause accepts comma-separated expressions similar to SELECT statement columns, with optional AS aliases. The wildcard (*) expands to all non-hidden columns of the modified table.

#### Key Behaviors

**Value References:**
- For INSERT/UPDATE: column references reflect values *after* changes apply
- For DELETE: column references show values *before* deletion occurs

**Processing Mechanics:**
All database modifications complete during the first `sqlite3_step()` call, with RETURNING output accumulated in memory. Subsequent calls retrieve result rows. However, "the order of individual RETURNING rows will match the order in which those rows were changed" is not guaranteed.

**UPSERT Handling:**
A RETURNING clause in an UPSERT statement reports both inserted and updated rows.

#### Major Limitations

1. Unavailable for virtual table DELETE/UPDATE operations
2. Restricted to top-level statements (not within triggers)
3. Cannot function as subqueries or feed into other queries
4. Output rows appear in arbitrary, non-deterministic order
5. Reflects pre-trigger values, not post-trigger modifications
6. Cannot contain top-level aggregate or window functions
7. UPDATE FROM statements cannot reference auxiliary tables in RETURNING

---

### ON CONFLICT Clause

The ON CONFLICT clause is a SQLite-specific extension that handles constraint violations across multiple SQL commands.

#### Syntax

For CREATE TABLE:
```sql
column-constraint ON CONFLICT resolution-algorithm
table-constraint ON CONFLICT resolution-algorithm
```

For INSERT and UPDATE:
```sql
INSERT OR resolution-algorithm ...
UPDATE OR resolution-algorithm ...
```

It has existed since before version 3.0.0 (2004), distinct from the UPSERT feature added in version 3.24.0.

#### Applicable Constraints

The clause applies to UNIQUE, NOT NULL, CHECK, and PRIMARY KEY constraints, but notably does not apply to FOREIGN KEY constraints.

#### Five Resolution Algorithms

**ROLLBACK**: "aborts the current SQL statement with an SQLITE_CONSTRAINT error and rolls back the current transaction."

**ABORT**: The default behavior. "aborts the current SQL statement with an SQLITE_CONSTRAINT error and backs out any changes made by the current SQL statement; but changes caused by prior SQL statements within the same transaction are preserved."

**FAIL**: Aborts the statement but preserves prior changes within that statement and keeps the transaction active.

**IGNORE**: "skips the one row that contains the constraint violation and continues processing subsequent rows."

**REPLACE**: Deletes conflicting rows before inserting/updating, or replaces NULL values with defaults for NOT NULL violations.

#### Default Behavior

When no algorithm is specified, ABORT is used automatically.

---

### UPSERT

UPSERT is a SQLite extension to the INSERT statement that allows it to behave as an UPDATE or no-op when a uniqueness constraint would be violated.

#### Syntax

```sql
INSERT INTO table ...
ON CONFLICT [(conflict-target)] DO UPDATE SET ... [WHERE ...]
ON CONFLICT [(conflict-target)] DO NOTHING
```

"UPSERT is not standard SQL. UPSERT in SQLite follows the syntax established by PostgreSQL, with generalizations."

The basic syntax follows this pattern:
- An ordinary INSERT statement
- Followed by one or more ON CONFLICT clauses
- Each clause specifies a conflict target and an action (DO NOTHING or DO UPDATE)

The conflict target identifies which uniqueness constraint triggers the upsert behavior.

#### Key Behaviors

**Constraint Scope**: UPSERT only applies to uniqueness constraints (UNIQUE or PRIMARY KEY constraints, or unique indexes). It does not intervene for NOT NULL, CHECK, or foreign key constraint violations.

**Row-by-Row Processing**: In multi-row inserts, the upsert decision is made independently for each row.

**Column References**: In DO UPDATE expressions, column names reference original values. To access the would-be-inserted values, use the "excluded." table qualifier.

#### Practical Examples

**Example 1 - Counter Increment**:
```sql
CREATE TABLE vocabulary(word TEXT PRIMARY KEY, count INT DEFAULT 1);
INSERT INTO vocabulary(word) VALUES('jovial')
  ON CONFLICT(word) DO UPDATE SET count=count+1;
```

**Example 2 - Conditional Update**:
```sql
INSERT INTO phonebook2(name,phonenumber,validDate)
  VALUES('Alice','704-555-1212','2018-05-08')
  ON CONFLICT(name) DO UPDATE SET
    phonenumber=excluded.phonenumber,
    validDate=excluded.validDate
  WHERE excluded.validDate>phonebook2.validDate;
```

#### Important Limitations

- UPSERT does not work with virtual tables
- The DO UPDATE clause always uses ABORT conflict resolution; any constraint violation causes the entire INSERT to rollback

#### Version History

UPSERT was introduced in SQLite 3.24.0 (2018). Multiple ON CONFLICT clauses and conflict-target-less DO UPDATE were added in later versions.

---

### INDEXED BY Clause

The INDEXED BY clause is an SQLite-specific extension that mandates the query planner use a particular named index for DELETE, SELECT, or UPDATE operations.

#### Syntax

```sql
table-name INDEXED BY index-name
table-name NOT INDEXED
```

#### Key Functionality

**INDEXED BY index-name:** Forces use of a specific index. If that index doesn't exist or cannot be applied, the statement preparation fails.

**NOT INDEXED:** Prevents index usage (except rowid lookups from UNIQUE/PRIMARY KEY constraints).

#### Critical Design Philosophy

This is **not** a performance tuning hint. "The INDEXED BY clause does not give the optimizer hints about which index to use; it gives the optimizer a requirement of which index to use."

The feature's actual purpose is detecting unintended query plan changes during regression testing after schema modifications.

#### Recommended Usage

Developers should avoid INDEXED BY during design, implementation, and testing phases. It's intended only as a final safeguard when "locking down" a completed design—a last resort after exhausting other optimization approaches.

#### Alternatives

- Use the unary "+" operator to disqualify WHERE clause terms from index consideration
- Employ `sqlite3_stmt_status()` with relevant counters to detect index misuse at runtime

---

### REPLACE Statement

The REPLACE command in SQLite functions as an alias for the INSERT OR REPLACE variant of the INSERT command.

#### Syntax

```sql
REPLACE INTO table ...
```

"This alias is provided for compatibility other SQL database engines."

For comprehensive details about syntax, diagrams, and usage examples, consult the main INSERT command documentation, as REPLACE operates identically to INSERT OR REPLACE and shares the same functionality and parameters.

---

## Functions

### Core SQL Functions

**abs(X)** - Returns the absolute value of numeric argument X, or NULL if X is NULL.

**changes()** - "returns the number of database rows that were changed or inserted or deleted by the most recently completed INSERT, DELETE, or UPDATE statement"

**char(X1,X2,...,XN)** - Produces a string from Unicode code point values provided as integer arguments.

**coalesce(X,Y,...)** - Delivers the first non-NULL argument; requires minimum two arguments.

**concat(X,...)** - Joins string representations of all non-NULL arguments; returns empty string if all are NULL.

**concat_ws(SEP,X,...)** - Concatenates non-null arguments using specified separator; returns NULL if separator is NULL.

**format(FORMAT,...)** - "works like the sqlite3_mprintf() C-language function and the printf() function from the standard C library"

**glob(X,Y)** - Implements pattern matching; equivalent to "Y GLOB X" with reversed parameter order.

**hex(X)** - Interprets argument as BLOB and returns uppercase hexadecimal representation.

**iif(B1,V1,...) / if(B1,V1,...)** - Evaluates paired boolean-value arguments, returning value for first true condition.

**ifnull(X,Y)** - Returns first non-NULL argument or NULL if both are NULL; requires exactly two arguments.

**instr(X,Y)** - Locates first occurrence of Y within X, returning position plus one or zero if not found.

**last_insert_rowid()** - Provides the ROWID of the most recently inserted row from current connection.

**length(X)** - For strings, counts Unicode code points; for blobs, counts bytes; returns NULL if X is NULL.

**like(X,Y) / like(X,Y,Z)** - Implements pattern matching; equivalent to "Y LIKE X [ESCAPE Z]".

**likelihood(X,Y)** - Returns X unchanged; provides query planner hint about boolean probability (0.0-1.0).

**likely(X)** - Returns X unchanged; hints query planner that value is probably true.

**lower(X)** - Converts string to lowercase using current locale.

**ltrim(X) / ltrim(X,Y)** - Removes leading whitespace or specified characters from string.

**max(X,Y,...)** - Returns maximum value among arguments.

**min(X,Y,...)** - Returns minimum value among arguments.

**nullif(X,Y)** - Returns NULL if X equals Y, otherwise returns X.

**printf(FORMAT,...)** - Formats string like C printf function.

**quote(X)** - Returns text representation of X suitable for inclusion in SQL statement.

**random()** - Returns pseudo-random integer between -9223372036854775808 and +9223372036854775807.

**randomblob(N)** - Returns N-byte blob containing pseudo-random bytes.

**replace(X,Y,Z)** - Returns string formed by substituting Z for every occurrence of Y in X.

**round(X) / round(X,Y)** - Rounds X to Y decimal places (default 0).

**rtrim(X) / rtrim(X,Y)** - Removes trailing whitespace or specified characters from string.

**sign(X)** - Returns -1, 0, or +1 depending on whether X is negative, zero, or positive.

**soundex(X)** - Returns Soundex encoding of string X.

**sqlite_compileoption_get(N)** - Returns Nth compile-time option string.

**sqlite_compileoption_used(X)** - Returns true if X was a compile-time option.

**sqlite_offset(X)** - Returns byte offset in database file for column X.

**sqlite_source_id()** - Returns check-in identifier of SQLite source tree.

**sqlite_version()** - Returns SQLite version string.

**substr(X,Y,Z) / substring(X,Y,Z)** - Returns substring of X starting at Y for Z characters.

**total_changes()** - Returns total number of row changes since database connection opened.

**trim(X) / trim(X,Y)** - Removes leading and trailing whitespace or specified characters.

**typeof(X)** - Returns type of expression: "null", "integer", "real", "text", or "blob".

**unicode(X)** - Returns numeric Unicode code point for first character of string X.

**unlikely(X)** - Returns X unchanged; hints query planner that value is probably false.

**upper(X)** - Converts string to uppercase using current locale.

**zeroblob(N)** - Returns BLOB consisting of N zero bytes.

---

### Aggregate Functions

**avg(X)** - Computes the average of non-NULL values, returning a floating-point result or NULL if no non-NULL inputs exist.

**count(X) / count(*)** - Returns count of non-NULL X values, or total rows with count(*).

**group_concat(X) / group_concat(X,Y) / string_agg(X,Y)** - "Returns a string which is the concatenation of all non-NULL values of X" with optional separator Y (comma default).

**max(X)** - Returns the maximum value from the group, or NULL if all values are NULL.

**min(X)** - Returns the minimum non-NULL value from the group, or NULL if all values are NULL.

**sum(X) / total(X)** - Sums non-NULL values; sum() returns NULL for empty groups while total() returns 0.0. Total() always produces floating-point results.

#### Key Features

- DISTINCT keyword filters duplicates before aggregation
- FILTER clause restricts rows included in calculations
- ORDER BY clause determines input processing order for functions like string_agg()
- Custom aggregates can be defined via sqlite3_create_function()

---

### Date and Time Functions

SQLite provides seven scalar date/time functions:

**date()** - Returns the date as "YYYY-MM-DD" format. Accepts a time-value and optional modifiers.

**time()** - Returns time formatted as "HH:MM:SS" or "HH:MM:SS.SSS" with the subsec modifier. Takes a time-value and optional modifiers.

**datetime()** - Returns combined date and time as "YYYY-MM-DD HH:MM:SS" or with milliseconds using subsec modifier. Accepts time-value and modifiers.

**julianday()** - "Returns the Julian day - the fractional number of days since noon in Greenwich on November 24, 4714 B.C." Accepts time-value and modifiers.

**unixepoch()** - "Returns a unix timestamp - the number of seconds since 1970-01-01 00:00:00 UTC." Normally returns integers; with subsec modifier returns floating-point values.

**strftime()** - "Returns the date formatted according to the format string specified as the first argument." Supports standard C library substitutions plus %f (fractional seconds) and %J (Julian day number).

**timediff()** - Takes exactly two time-values. "Returns a string that describes the amount of time that must be added to B in order to reach time A" in format: (+|-)YYYY-MM-DD HH:MM:SS.SSS

#### Time Value Formats

SQLite accepts various time-value formats:
- YYYY-MM-DD
- YYYY-MM-DD HH:MM
- YYYY-MM-DD HH:MM:SS
- YYYY-MM-DD HH:MM:SS.SSS
- YYYY-MM-DDTHH:MM
- YYYY-MM-DDTHH:MM:SS
- YYYY-MM-DDTHH:MM:SS.SSS
- HH:MM
- HH:MM:SS
- HH:MM:SS.SSS
- now
- DDDDDDDDDD (Julian day number as integer or float)

#### Time Value Modifiers

Common modifiers include:
- NNN days
- NNN hours
- NNN minutes
- NNN seconds
- NNN months
- NNN years
- start of month
- start of year
- start of day
- weekday N
- unixepoch
- julianday
- auto
- localtime
- utc

---

## Keywords and Reserved Words

According to the documentation, SQLite recognizes 147 keywords that cannot be used as names for tables, indices, columns, databases, functions, collations, or other named objects without proper quoting.

The complete list includes:

ABORT, ACTION, ADD, AFTER, ALL, ALTER, ALWAYS, ANALYZE, AND, AS, ASC, ATTACH, AUTOINCREMENT, BEFORE, BEGIN, BETWEEN, BY, CASCADE, CASE, CAST, CHECK, COLLATE, COLUMN, COMMIT, CONFLICT, CONSTRAINT, CREATE, CROSS, CURRENT, CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP, DATABASE, DEFAULT, DEFERRABLE, DEFERRED, DELETE, DESC, DETACH, DISTINCT, DO, DROP, EACH, ELSE, END, ESCAPE, EXCEPT, EXCLUDE, EXCLUSIVE, EXISTS, EXPLAIN, FAIL, FILTER, FIRST, FOLLOWING, FOR, FOREIGN, FROM, FULL, GENERATED, GLOB, GROUP, GROUPS, HAVING, IF, IGNORE, IMMEDIATE, IN, INDEX, INDEXED, INITIALLY, INNER, INSERT, INSTEAD, INTERSECT, INTO, IS, ISNULL, JOIN, KEY, LAST, LEFT, LIKE, LIMIT, MATCH, MATERIALIZED, NATURAL, NO, NOT, NOTHING, NOTNULL, NULL, NULLS, OF, OFFSET, ON, OR, ORDER, OTHERS, OUTER, OVER, PARTITION, PLAN, PRAGMA, PRECEDING, PRIMARY, QUERY, RAISE, RANGE, RECURSIVE, REFERENCES, REGEXP, REINDEX, RELEASE, RENAME, REPLACE, RESTRICT, RETURNING, RIGHT, ROLLBACK, ROW, ROWS, SAVEPOINT, SELECT, SET, TABLE, TEMP, TEMPORARY, THEN, TIES, TO, TRANSACTION, TRIGGER, UNBOUNDED, UNION, UNIQUE, UPDATE, USING, VACUUM, VALUES, VIEW, VIRTUAL, WHEN, WHERE, WINDOW, WITH, WITHOUT

### Quoting Identifiers

To use keywords as identifiers, SQLite supports four quoting mechanisms:
- Single quotes: `'identifier'`
- Double quotes: `"identifier"`
- Square brackets: `[identifier]`
- Grave accents: `` `identifier` ``

---

## Comments

Comments are non-executable text that can appear within SQL queries. The parser treats them as whitespace and they can be positioned anywhere whitespace is permitted, including within expressions and across multiple lines.

### Comment Types

#### SQL-Style Comments (Line Comments)

```sql
-- This is a comment
SELECT * FROM table; -- This is also a comment
```

- Begin with two consecutive hyphens: `--`
- Extend to the next newline character or end of input
- Cannot span multiple lines

#### C-Style Comments (Block Comments)

```sql
/* This is a comment */
SELECT * FROM /* inline comment */ table;
/*
  Multi-line
  comment
*/
```

- Begin with `/*` and end with `*/`
- Can span multiple lines
- Extend to the closing pair or end of input

### Key Characteristics

"Comments can appear anywhere whitespace can occur, including inside expressions and in the middle of other SQL statements."

Important limitation: "Comments do not nest," meaning you cannot embed one comment type within another.

### Usage Context

These comments function within SQL queries passed to database preparation interfaces like `sqlite3_prepare_v2()`. The parser recognizes them as whitespace equivalents, allowing flexible placement throughout query text without affecting execution.

---

## Additional Resources

For more detailed information about SQLite syntax, consult the official documentation at:
- https://sqlite.org/lang.html
- https://sqlite.org/syntax.html

---

*Reference generated on 2025-10-17 from SQLite official documentation*
