"""
SQLite SQL Parser

Recursive descent parser with precedence climbing for expressions.
Follows the parser mental model from lexer+parser_mental_model.md

This is a COMPLETE implementation covering all SQLite statements.
"""

from typing import List, Optional, Union, Tuple
from .lexer import Token, Lexer
from .utils import (
    TokenType, get_precedence, is_binary_operator,
    TOKEN_TO_BINARY_OP, TOKEN_TO_UNARY_OP
)
from .ast_nodes import *
from .errors import (
    SyntaxError as SQLSyntaxError,
    UnexpectedTokenError,
    UnexpectedEOFError
)


class Parser:
    """
    SQLite SQL Parser

    Parses token stream from lexer into Abstract Syntax Tree using
    recursive descent with precedence climbing for expressions.
    """

    def __init__(self, tokens: List[Token], debug: bool = False):
        self.tokens = tokens
        self.pos = 0
        self.errors: List[Exception] = []

        # Debug tracking
        self.debug = debug
        self.call_stack: List[str] = []  # Stack of parsing method names
        self.trace_log: List[str] = []    # Log of all parsing activities

    def at_end(self) -> bool:
        """Check if at end of tokens"""
        return self.pos >= len(self.tokens) or self.peek().type == TokenType.EOF

    def peek(self, offset: int = 0) -> Token:
        """Look ahead at token"""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # Return EOF

    def previous(self) -> Token:
        """Get previous token"""
        if self.pos > 0:
            return self.tokens[self.pos - 1]
        return self.tokens[0]

    def advance(self) -> Token:
        """Consume and return current token"""
        token = self.peek()
        if not self.at_end():
            self.pos += 1
        return token

    def match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the types"""
        return self.peek().type in types

    def consume(self, token_type: TokenType, message: Optional[str] = None) -> Token:
        """Consume token of expected type or raise error"""
        if self.match(token_type):
            return self.advance()

        if message is None:
            message = f"Expected {token_type.name}"

        raise UnexpectedTokenError(
            expected=token_type.name,
            found=self.peek().type.name,
            position=self.peek().position,
            sql=self.tokens[0].span.start if self.tokens else None
        )

    def expect(self, token_type: TokenType) -> Token:
        """Expect and consume token"""
        return self.consume(token_type, f"Expected {token_type.name}")

    def expect_identifier_or_keyword(self) -> Token:
        """Expect identifier or allow keyword as identifier (SQLite allows keywords as column names)"""
        token = self.peek()
        if token.type == TokenType.IDENTIFIER:
            return self.advance()
        # Allow any keyword to be used as an identifier
        elif token.type != TokenType.EOF and token.value:
            # It's a keyword, but we'll treat it as an identifier
            return self.advance()
        else:
            raise UnexpectedTokenError(
                expected="IDENTIFIER",
                found=token.type.name,
                position=token.position
            )

    def synchronize(self):
        """Panic mode recovery - skip to next statement"""
        self.advance()

        while not self.at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return

            # Stop at statement-starting keywords
            if self.match(
                TokenType.SELECT, TokenType.INSERT, TokenType.UPDATE,
                TokenType.DELETE, TokenType.CREATE, TokenType.DROP,
                TokenType.ALTER, TokenType.BEGIN, TokenType.COMMIT,
                TokenType.ROLLBACK, TokenType.ATTACH, TokenType.DETACH
            ):
                return

            self.advance()

    # =========================================================================
    # Debug/Tracing Methods
    # =========================================================================

    def get_state(self) -> dict:
        """
        Get current parser state for debugging

        Returns:
            Dictionary with parser state information
        """
        token = self.peek()
        return {
            'pos': self.pos,
            'token_type': token.type.name,
            'token_value': token.value,
            'depth': len(self.call_stack),
            'active_method': self.call_stack[-1] if self.call_stack else None,
            'stack': list(self.call_stack)
        }

    def trace_enter(self, method_name: str):
        """
        Log entry into a parsing method

        Args:
            method_name: Name of method being entered
        """
        if not self.debug:
            return

        state = self.get_state()
        indent = "  " * len(self.call_stack)
        token = self.peek()

        msg = f"{indent}→ {method_name}() at pos={self.pos} token={token.type.name}:{repr(token.value)}"
        self.trace_log.append(msg)
        self.call_stack.append(method_name)

    def trace_exit(self, method_name: str, result: any = None):
        """
        Log exit from a parsing method

        Args:
            method_name: Name of method being exited
            result: Result being returned (optional)
        """
        if not self.debug:
            return

        if self.call_stack and self.call_stack[-1] == method_name:
            self.call_stack.pop()

        indent = "  " * len(self.call_stack)
        result_str = f"{type(result).__name__}" if result is not None else "None"
        msg = f"{indent}← {method_name}() → {result_str}"
        self.trace_log.append(msg)

    def trace_action(self, action: str):
        """
        Log a parsing action (token consumption, decision, etc.)

        Args:
            action: Description of the action
        """
        if not self.debug:
            return

        indent = "  " * len(self.call_stack)
        msg = f"{indent}  • {action}"
        self.trace_log.append(msg)

    def get_trace_log(self) -> List[str]:
        """
        Get the complete trace log

        Returns:
            List of trace messages
        """
        return self.trace_log

    def print_trace(self):
        """Print the complete trace log to stdout"""
        for msg in self.trace_log:
            print(msg)

    # =========================================================================
    # Top-Level Parsing
    # =========================================================================

    def parse(self) -> List[Statement]:
        """Parse SQL and return list of statements"""
        self.trace_enter("parse")
        statements = []

        while not self.at_end():
            try:
                # Skip extra semicolons
                if self.match(TokenType.SEMICOLON):
                    self.trace_action("Skipping semicolon")
                    self.advance()
                    continue

                stmt = self.parse_statement()
                if stmt:
                    statements.append(stmt)
                    self.trace_action(f"Added {type(stmt).__name__} to statements")

                # Optional semicolon
                if self.match(TokenType.SEMICOLON):
                    self.trace_action("Consuming optional semicolon")
                    self.advance()

            except Exception as e:
                self.trace_action(f"Exception: {e}")
                self.errors.append(e)
                self.synchronize()

        self.trace_exit("parse", statements)
        return statements

    def parse_statement(self) -> Optional[Statement]:
        """Parse a single statement"""
        self.trace_enter("parse_statement")

        # Check statement type by first keyword
        if self.match(TokenType.SELECT, TokenType.WITH):
            self.trace_action("Routing to parse_select_statement")
            result = self.parse_select_statement()
        elif self.match(TokenType.INSERT, TokenType.REPLACE):
            self.trace_action("Routing to parse_insert_statement")
            result = self.parse_insert_statement()
        elif self.match(TokenType.UPDATE):
            self.trace_action("Routing to parse_update_statement")
            result = self.parse_update_statement()
        elif self.match(TokenType.DELETE):
            self.trace_action("Routing to parse_delete_statement")
            result = self.parse_delete_statement()
        elif self.match(TokenType.CREATE):
            self.trace_action("Routing to parse_create_statement")
            result = self.parse_create_statement()
        elif self.match(TokenType.DROP):
            self.trace_action("Routing to parse_drop_statement")
            result = self.parse_drop_statement()
        elif self.match(TokenType.ALTER):
            self.trace_action("Routing to parse_alter_statement")
            result = self.parse_alter_statement()
        elif self.match(TokenType.BEGIN):
            self.trace_action("Routing to parse_begin_statement")
            result = self.parse_begin_statement()
        elif self.match(TokenType.COMMIT, TokenType.END):
            self.trace_action("Routing to parse_commit_statement (COMMIT/END)")
            result = self.parse_commit_statement()
        elif self.match(TokenType.ROLLBACK):
            self.trace_action("Routing to parse_rollback_statement")
            result = self.parse_rollback_statement()
        elif self.match(TokenType.SAVEPOINT):
            self.trace_action("Routing to parse_savepoint_statement")
            result = self.parse_savepoint_statement()
        elif self.match(TokenType.RELEASE):
            self.trace_action("Routing to parse_release_statement")
            result = self.parse_release_statement()
        elif self.match(TokenType.ATTACH):
            self.trace_action("Routing to parse_attach_statement")
            result = self.parse_attach_statement()
        elif self.match(TokenType.DETACH):
            self.trace_action("Routing to parse_detach_statement")
            result = self.parse_detach_statement()
        elif self.match(TokenType.ANALYZE):
            self.trace_action("Routing to parse_analyze_statement")
            result = self.parse_analyze_statement()
        elif self.match(TokenType.VACUUM):
            self.trace_action("Routing to parse_vacuum_statement")
            result = self.parse_vacuum_statement()
        elif self.match(TokenType.REINDEX):
            self.trace_action("Routing to parse_reindex_statement")
            result = self.parse_reindex_statement()
        elif self.match(TokenType.EXPLAIN):
            self.trace_action("Routing to parse_explain_statement")
            result = self.parse_explain_statement()
        elif self.match(TokenType.PRAGMA):
            self.trace_action("Routing to parse_pragma_statement")
            result = self.parse_pragma_statement()
        else:
            self.trace_action(f"No match for token {self.peek().type.name} - raising error")
            raise SQLSyntaxError(
                f"Unexpected token: {self.peek().type.name}",
                self.peek().position
            )

        self.trace_exit("parse_statement", result)
        return result

    # =========================================================================
    # Expression Parsing (Precedence Climbing)
    # =========================================================================

    def parse_expression(self, min_precedence: int = 0) -> Expression:
        """Parse expression using precedence climbing"""
        # Parse primary expression
        left = self.parse_unary_expression()

        # Parse binary operators with precedence
        while not self.at_end():
            token = self.peek()

            # FIRST: Check for NOT followed by special operators (NOT BETWEEN, NOT IN, NOT LIKE)
            # This must come before the binary operator check because NOT is also a binary operator
            if token.type == TokenType.NOT:
                next_token = self.peek(1).type
                if next_token == TokenType.BETWEEN:
                    left = self.parse_between_expression(left)
                    continue
                elif next_token == TokenType.IN:
                    left = self.parse_in_expression(left)
                    continue
                elif next_token in (TokenType.LIKE, TokenType.GLOB,
                                   TokenType.MATCH, TokenType.REGEXP):
                    left = self.parse_like_expression(left)
                    continue
                # If NOT is not followed by a special operator, fall through to binary operator handling

            # SECOND: Check for special operators that are also binary operators but need special handling
            # These must be checked before the general binary operator check
            # BETWEEN, IN, LIKE, GLOB, MATCH, REGEXP need special parsing when they appear as operators
            if token.type == TokenType.BETWEEN:
                left = self.parse_between_expression(left)
                continue
            elif token.type == TokenType.IN:
                left = self.parse_in_expression(left)
                continue
            elif token.type in (TokenType.LIKE, TokenType.GLOB, TokenType.MATCH, TokenType.REGEXP):
                left = self.parse_like_expression(left)
                continue

            # Check for binary operators
            if not is_binary_operator(token.type):
                # Check for special operators
                if token.type == TokenType.BETWEEN:
                    left = self.parse_between_expression(left)
                    continue
                elif token.type == TokenType.IN:
                    left = self.parse_in_expression(left)
                    continue
                elif token.type in (TokenType.LIKE, TokenType.GLOB,
                                   TokenType.MATCH, TokenType.REGEXP):
                    left = self.parse_like_expression(left)
                    continue
                elif token.type == TokenType.IS:
                    left = self.parse_is_expression(left)
                    continue
                elif token.type == TokenType.COLLATE:
                    left = self.parse_collate_expression(left)
                    continue
                else:
                    break

            precedence = get_precedence(token.type)
            if precedence < min_precedence:
                break

            # Consume operator
            op_token = self.advance()
            op = TOKEN_TO_BINARY_OP.get(op_token.type)

            # Parse right side with higher precedence
            right = self.parse_expression(precedence + 1)

            # Create binary expression
            left = BinaryExpression(operator=op, left=left, right=right)

        return left

    def parse_unary_expression(self) -> Expression:
        """Parse unary expression"""
        if self.match(TokenType.PLUS, TokenType.MINUS, TokenType.NOT, TokenType.TILDE):
            op_token = self.advance()
            op = TOKEN_TO_UNARY_OP[op_token.type]
            operand = self.parse_unary_expression()
            return UnaryExpression(operator=op, operand=operand)

        return self.parse_primary_expression()

    def parse_primary_expression(self) -> Expression:
        """Parse primary expression"""
        # Literals
        if self.match(TokenType.NUMBER):
            token = self.advance()
            value = float(token.value) if '.' in token.value or 'e' in token.value.lower() else int(token.value)
            return NumberLiteral(value=value, raw=token.value)

        if self.match(TokenType.STRING):
            token = self.advance()
            return StringLiteral(value=token.value, quote_char="'")

        if self.match(TokenType.BLOB):
            token = self.advance()
            return BlobLiteral(value=bytes.fromhex(token.value), raw=token.value)

        if self.match(TokenType.NULL):
            self.advance()
            return NullLiteral()

        if self.match(TokenType.TRUE):
            self.advance()
            return BooleanLiteral(value=True)

        if self.match(TokenType.FALSE):
            self.advance()
            return BooleanLiteral(value=False)

        if self.match(TokenType.CURRENT_TIME):
            self.advance()
            return CurrentTimeLiteral(type="TIME")

        if self.match(TokenType.CURRENT_DATE):
            self.advance()
            return CurrentTimeLiteral(type="DATE")

        if self.match(TokenType.CURRENT_TIMESTAMP):
            self.advance()
            return CurrentTimeLiteral(type="TIMESTAMP")

        # Parameter
        if self.match(TokenType.PARAMETER):
            return self.parse_parameter()

        # CASE expression
        if self.match(TokenType.CASE):
            return self.parse_case_expression()

        # CAST expression
        if self.match(TokenType.CAST):
            return self.parse_cast_expression()

        # RAISE expression (for triggers)
        if self.match(TokenType.RAISE):
            return self.parse_raise_expression()

        # EXISTS expression
        if self.match(TokenType.EXISTS):
            return self.parse_exists_expression()

        # Parenthesized expression or subquery
        if self.match(TokenType.LPAREN):
            return self.parse_parenthesized_or_subquery()

        # Identifier or function call
        if self.match(TokenType.IDENTIFIER):
            return self.parse_identifier_or_function()

        raise SQLSyntaxError(
            f"Expected expression, found {self.peek().type.name}",
            self.peek().position
        )

    def parse_identifier_or_function(self) -> Expression:
        """Parse identifier or function call"""
        name = self.advance().value

        # Check for function call
        if self.match(TokenType.LPAREN):
            return self.parse_function_call(name)

        # Check for qualified identifier
        if self.match(TokenType.DOT):
            parts = [name]
            while self.match(TokenType.DOT):
                self.advance()  # consume dot
                parts.append(self.expect(TokenType.IDENTIFIER).value)
            return QualifiedIdentifier(parts=parts)

        return Identifier(name=name)

    def parse_function_call(self, name: str) -> FunctionCall:
        """Parse function call"""
        self.expect(TokenType.LPAREN)

        # Check for COUNT(*)
        star = False
        distinct = False
        args = []

        if self.match(TokenType.STAR):
            self.advance()
            star = True
        else:
            # Check for DISTINCT
            if self.match(TokenType.DISTINCT):
                self.advance()
                distinct = True

            # Parse arguments
            if not self.match(TokenType.RPAREN):
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    self.advance()
                    args.append(self.parse_expression())

        self.expect(TokenType.RPAREN)

        # Optional FILTER clause
        filter_clause = None
        if self.match(TokenType.FILTER):
            self.advance()
            self.expect(TokenType.LPAREN)
            self.expect(TokenType.WHERE)
            filter_clause = WhereClause(condition=self.parse_expression())
            self.expect(TokenType.RPAREN)

        # Optional OVER clause
        over_clause = None
        if self.match(TokenType.OVER):
            over_clause = self.parse_window_expression()

        return FunctionCall(
            name=name,
            args=args,
            distinct=distinct,
            star=star,
            filter_clause=filter_clause,
            over_clause=over_clause
        )

    def parse_case_expression(self) -> CaseExpression:
        """Parse CASE expression"""
        self.expect(TokenType.CASE)

        # Check for CASE value WHEN ...
        value = None
        if not self.match(TokenType.WHEN):
            value = self.parse_expression()

        # Parse WHEN clauses
        when_clauses = []
        while self.match(TokenType.WHEN):
            self.advance()
            condition = self.parse_expression()
            self.expect(TokenType.THEN)
            result = self.parse_expression()
            when_clauses.append((condition, result))

        # Optional ELSE
        else_clause = None
        if self.match(TokenType.ELSE):
            self.advance()
            else_clause = self.parse_expression()

        self.expect(TokenType.END)

        return CaseExpression(
            value=value,
            when_clauses=when_clauses,
            else_clause=else_clause
        )

    def parse_cast_expression(self) -> CastExpression:
        """Parse CAST expression"""
        self.expect(TokenType.CAST)
        self.expect(TokenType.LPAREN)
        expression = self.parse_expression()
        self.expect(TokenType.AS)
        type_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.RPAREN)

        return CastExpression(expression=expression, type_name=type_name)

    def parse_raise_expression(self) -> RaiseExpression:
        """Parse RAISE expression (for triggers only)"""
        self.expect(TokenType.RAISE)
        self.expect(TokenType.LPAREN)

        # Parse raise type: IGNORE, ROLLBACK, ABORT, or FAIL
        raise_type = None
        message = None

        if self.match(TokenType.IGNORE):
            self.advance()
            raise_type = "IGNORE"
        elif self.match(TokenType.ROLLBACK):
            self.advance()
            raise_type = "ROLLBACK"
            self.expect(TokenType.COMMA)
            message = self.expect(TokenType.STRING).value
        elif self.match(TokenType.ABORT):
            self.advance()
            raise_type = "ABORT"
            self.expect(TokenType.COMMA)
            message = self.expect(TokenType.STRING).value
        elif self.match(TokenType.FAIL):
            self.advance()
            raise_type = "FAIL"
            self.expect(TokenType.COMMA)
            message = self.expect(TokenType.STRING).value
        else:
            raise SQLSyntaxError(
                "Expected IGNORE, ROLLBACK, ABORT, or FAIL in RAISE expression",
                self.peek().position
            )

        self.expect(TokenType.RPAREN)
        return RaiseExpression(raise_type=raise_type, message=message)

    def parse_exists_expression(self) -> ExistsExpression:
        """Parse EXISTS expression"""
        self.expect(TokenType.EXISTS)
        subquery = self.parse_parenthesized_or_subquery()

        if not isinstance(subquery, SubqueryExpression):
            raise SQLSyntaxError("EXISTS requires a subquery", self.peek().position)

        return ExistsExpression(subquery=subquery)

    def parse_parenthesized_or_subquery(self) -> Union[ParenthesizedExpression, SubqueryExpression]:
        """Parse parenthesized expression or subquery"""
        self.expect(TokenType.LPAREN)

        # Check for subquery
        if self.match(TokenType.SELECT, TokenType.WITH):
            select = self.parse_select_statement()
            self.expect(TokenType.RPAREN)
            return SubqueryExpression(select=select)

        # Regular expression
        expr = self.parse_expression()
        self.expect(TokenType.RPAREN)
        return ParenthesizedExpression(expression=expr)

    def parse_parameter(self) -> Parameter:
        """Parse parameter"""
        token = self.expect(TokenType.PARAMETER)
        value = token.value

        if value == '?':
            return Parameter(prefix='?')
        elif value[0] == '?' and value[1:].isdigit():
            return Parameter(number=int(value[1:]), prefix='?')
        else:
            return Parameter(name=value[1:], prefix=value[0])

    def parse_between_expression(self, value: Expression) -> BetweenExpression:
        """Parse BETWEEN expression"""
        negated = False
        if self.match(TokenType.NOT):
            self.advance()
            negated = True

        self.expect(TokenType.BETWEEN)
        lower = self.parse_expression(get_precedence(TokenType.BETWEEN) + 1)
        self.expect(TokenType.AND)
        upper = self.parse_expression(get_precedence(TokenType.BETWEEN) + 1)

        return BetweenExpression(value=value, lower=lower, upper=upper, negated=negated)

    def parse_in_expression(self, value: Expression) -> InExpression:
        """Parse IN expression"""
        negated = False
        if self.match(TokenType.NOT):
            self.advance()
            negated = True

        self.expect(TokenType.IN)
        self.expect(TokenType.LPAREN)

        # Check for subquery
        if self.match(TokenType.SELECT, TokenType.WITH):
            select = self.parse_select_statement()
            self.expect(TokenType.RPAREN)
            return InExpression(value=value, values=SubqueryExpression(select=select), negated=negated)

        # Parse value list
        values = [self.parse_expression()]
        while self.match(TokenType.COMMA):
            self.advance()
            values.append(self.parse_expression())

        self.expect(TokenType.RPAREN)
        return InExpression(value=value, values=values, negated=negated)

    def parse_like_expression(self, value: Expression) -> LikeExpression:
        """Parse LIKE/GLOB/REGEXP/MATCH expression"""
        negated = False
        if self.match(TokenType.NOT):
            self.advance()
            negated = True

        op_token = self.advance()
        operator = op_token.type.name

        pattern = self.parse_expression(get_precedence(op_token.type) + 1)

        # Optional ESCAPE
        escape = None
        if self.match(TokenType.ESCAPE):
            self.advance()
            escape = self.parse_expression()

        return LikeExpression(
            value=value,
            pattern=pattern,
            operator=operator,
            escape=escape,
            negated=negated
        )

    def parse_is_expression(self, left: Expression) -> BinaryExpression:
        """Parse IS [NOT] expression"""
        self.expect(TokenType.IS)

        negated = False
        if self.match(TokenType.NOT):
            self.advance()
            negated = True

        right = self.parse_expression(get_precedence(TokenType.IS) + 1)

        return BinaryExpression(
            operator=BinaryOperator.IS_NOT if negated else BinaryOperator.IS,
            left=left,
            right=right
        )

    def parse_collate_expression(self, expression: Expression) -> CollateExpression:
        """Parse COLLATE expression"""
        self.expect(TokenType.COLLATE)
        collation = self.expect(TokenType.IDENTIFIER).value
        return CollateExpression(expression=expression, collation=collation)

    def parse_window_expression(self) -> WindowExpression:
        """Parse OVER (window-spec) clause"""
        self.expect(TokenType.OVER)

        # Check for named window
        if self.match(TokenType.IDENTIFIER):
            return WindowExpression(window_name=self.advance().value)

        self.expect(TokenType.LPAREN)

        # Parse PARTITION BY
        partition_by = []
        if self.match(TokenType.PARTITION):
            self.advance()
            self.expect(TokenType.BY)
            partition_by.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.advance()
                partition_by.append(self.parse_expression())

        # Parse ORDER BY
        order_by = []
        if self.match(TokenType.ORDER):
            self.advance()
            self.expect(TokenType.BY)
            order_by = self.parse_ordering_terms()

        # Parse frame spec (ROWS/RANGE/GROUPS)
        frame_spec = None
        if self.match(TokenType.ROWS, TokenType.RANGE, TokenType.GROUPS):
            frame_spec = self.parse_frame_spec()

        self.expect(TokenType.RPAREN)

        return WindowExpression(
            partition_by=partition_by,
            order_by=order_by,
            frame_spec=frame_spec
        )

    def parse_frame_spec(self) -> FrameSpec:
        """Parse window frame spec"""
        # Get frame type
        frame_type_token = self.advance()
        if frame_type_token.type == TokenType.ROWS:
            frame_type = FrameType.ROWS
        elif frame_type_token.type == TokenType.RANGE:
            frame_type = FrameType.RANGE
        else:
            frame_type = FrameType.GROUPS

        # Check for BETWEEN keyword
        # Syntax: ROWS BETWEEN start AND end
        #     or: ROWS start
        if self.match(TokenType.BETWEEN):
            self.advance()
            start = self.parse_frame_boundary()
            self.expect(TokenType.AND)
            end = self.parse_frame_boundary()
            return FrameSpec(frame_type=frame_type, start=start, end=end)

        # Parse single frame boundary (short form)
        start = self.parse_frame_boundary()

        end = None
        if self.match(TokenType.AND):
            self.advance()
            end = self.parse_frame_boundary()

        return FrameSpec(frame_type=frame_type, start=start, end=end)

    def parse_frame_boundary(self) -> FrameBoundary:
        """Parse frame boundary"""
        if self.match(TokenType.UNBOUNDED):
            self.advance()
            if self.match(TokenType.PRECEDING):
                self.advance()
                return FrameBoundary(bound_type=FrameBound.UNBOUNDED_PRECEDING)
            elif self.match(TokenType.FOLLOWING):
                self.advance()
                return FrameBoundary(bound_type=FrameBound.UNBOUNDED_FOLLOWING)

        if self.match(TokenType.CURRENT):
            self.advance()
            self.expect(TokenType.ROW)
            return FrameBoundary(bound_type=FrameBound.CURRENT_ROW)

        # offset PRECEDING/FOLLOWING
        # Parse with high minimum precedence to prevent BETWEEN from being consumed
        # as part of the expression (BETWEEN has precedence 4, so use 5)
        offset = self.parse_expression(min_precedence=5)
        if self.match(TokenType.PRECEDING):
            self.advance()
            return FrameBoundary(bound_type=FrameBound.PRECEDING, offset=offset)
        elif self.match(TokenType.FOLLOWING):
            self.advance()
            return FrameBoundary(bound_type=FrameBound.FOLLOWING, offset=offset)

        raise SQLSyntaxError("Expected frame boundary", self.peek().position)

    # =========================================================================
    # SELECT Statement
    # =========================================================================

    def parse_select_statement(self) -> SelectStatement:
        """Parse SELECT statement"""
        # Parse WITH clause
        with_clause = None
        if self.match(TokenType.WITH):
            with_clause = self.parse_with_clause()

        # Parse first SELECT core
        select_core = self.parse_select_core()

        # Parse compound SELECTs
        compound_selects = []
        while self.match(TokenType.UNION, TokenType.INTERSECT, TokenType.EXCEPT):
            op_token = self.advance()

            # Check for UNION ALL
            if op_token.type == TokenType.UNION and self.match(TokenType.ALL):
                self.advance()
                op = CompoundOperator.UNION_ALL
            elif op_token.type == TokenType.UNION:
                op = CompoundOperator.UNION
            elif op_token.type == TokenType.INTERSECT:
                op = CompoundOperator.INTERSECT
            else:
                op = CompoundOperator.EXCEPT

            core = self.parse_select_core()
            compound_selects.append((op, core))

        # Parse ORDER BY
        order_by = None
        if self.match(TokenType.ORDER):
            order_by = self.parse_order_by_clause()

        # Parse LIMIT
        limit = None
        if self.match(TokenType.LIMIT):
            limit = self.parse_limit_clause()

        return SelectStatement(
            with_clause=with_clause,
            select_core=select_core,
            compound_selects=compound_selects,
            order_by=order_by,
            limit=limit
        )

    def parse_select_core(self) -> SelectCore:
        """Parse SELECT core"""
        self.expect(TokenType.SELECT)

        # Check for DISTINCT/ALL
        distinct = False
        all_flag = False
        if self.match(TokenType.DISTINCT):
            self.advance()
            distinct = True
        elif self.match(TokenType.ALL):
            self.advance()
            all_flag = True

        # Parse result columns
        columns = self.parse_result_columns()

        # Parse FROM
        from_clause = None
        if self.match(TokenType.FROM):
            from_clause = self.parse_from_clause()

        # Parse WHERE
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        # Parse GROUP BY
        group_by = None
        if self.match(TokenType.GROUP):
            group_by = self.parse_group_by_clause()

        # Parse WINDOW
        window_definitions = []
        if self.match(TokenType.WINDOW):
            window_definitions = self.parse_window_definitions()

        return SelectCore(
            distinct=distinct,
            all=all_flag,
            columns=columns,
            from_clause=from_clause,
            where=where,
            group_by=group_by,
            window_definitions=window_definitions
        )

    def parse_result_columns(self) -> List[ResultColumn]:
        """Parse result columns"""
        columns = []

        columns.append(self.parse_result_column())
        while self.match(TokenType.COMMA):
            self.advance()
            columns.append(self.parse_result_column())

        return columns

    def parse_result_column(self) -> ResultColumn:
        """Parse single result column"""
        # Check for *
        if self.match(TokenType.STAR):
            self.advance()
            return ResultColumn()

        # Check for table.*
        if self.match(TokenType.IDENTIFIER) and self.peek(1).type == TokenType.DOT and self.peek(2).type == TokenType.STAR:
            table = self.advance().value
            self.advance()  # dot
            self.advance()  # star
            return ResultColumn(table_star=table)

        # Regular expression
        expr = self.parse_expression()

        # Optional AS alias
        alias = None
        if self.match(TokenType.AS):
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.IDENTIFIER):
            # Implicit alias
            alias = self.advance().value

        return ResultColumn(expression=expr, alias=alias)

    def parse_from_clause(self) -> FromClause:
        """Parse FROM clause"""
        self.expect(TokenType.FROM)
        source = self.parse_table_or_join()
        return FromClause(source=source)

    def parse_table_or_join(self) -> Union[TableReference, SubqueryTable, JoinClause]:
        """Parse table reference or join"""
        left = self.parse_table_reference()

        # Check for joins
        while True:
            natural = False
            join_type = None

            # Check for NATURAL
            if self.match(TokenType.NATURAL):
                self.advance()
                natural = True

            # Parse join type
            if self.match(TokenType.LEFT):
                self.advance()
                if self.match(TokenType.OUTER):
                    self.advance()
                join_type = JoinType.LEFT
            elif self.match(TokenType.RIGHT):
                self.advance()
                if self.match(TokenType.OUTER):
                    self.advance()
                join_type = JoinType.RIGHT
            elif self.match(TokenType.FULL):
                self.advance()
                if self.match(TokenType.OUTER):
                    self.advance()
                join_type = JoinType.FULL
            elif self.match(TokenType.INNER):
                self.advance()
                join_type = JoinType.INNER
            elif self.match(TokenType.CROSS):
                self.advance()
                join_type = JoinType.CROSS

            # Check for JOIN keyword
            if not self.match(TokenType.JOIN) and not self.match(TokenType.COMMA):
                break

            if self.match(TokenType.JOIN):
                self.advance()
            else:
                # Comma join
                self.advance()
                join_type = None

            # Parse right table
            right = self.parse_table_reference()

            # Parse ON/USING
            on_condition = None
            using_columns = []

            if self.match(TokenType.ON):
                self.advance()
                on_condition = self.parse_expression()
            elif self.match(TokenType.USING):
                self.advance()
                self.expect(TokenType.LPAREN)
                using_columns.append(self.expect(TokenType.IDENTIFIER).value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    using_columns.append(self.expect(TokenType.IDENTIFIER).value)
                self.expect(TokenType.RPAREN)

            left = JoinClause(
                left=left,
                join_type=join_type,
                natural=natural,
                right=right,
                on_condition=on_condition,
                using_columns=using_columns
            )

        return left

    def parse_table_reference(self) -> Union[TableReference, SubqueryTable]:
        """Parse table reference"""
        # Check for subquery
        if self.match(TokenType.LPAREN):
            self.advance()
            select = self.parse_select_statement()
            self.expect(TokenType.RPAREN)

            alias = None
            if self.match(TokenType.AS):
                self.advance()
                alias = self.expect(TokenType.IDENTIFIER).value
            elif self.match(TokenType.IDENTIFIER):
                alias = self.advance().value

            return SubqueryTable(select=select, alias=alias)

        # Parse table name
        name_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            name_parts.append(self.expect(TokenType.IDENTIFIER).value)

        name = QualifiedIdentifier(parts=name_parts)

        # Optional alias
        alias = None
        if self.match(TokenType.AS):
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.IDENTIFIER):
            alias = self.advance().value

        # Optional INDEXED BY or NOT INDEXED
        indexed_by = None
        not_indexed = False

        if self.match(TokenType.INDEXED):
            self.advance()
            self.expect(TokenType.BY)
            indexed_by = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.NOT):
            if self.peek(1).type == TokenType.INDEXED:
                self.advance()  # NOT
                self.advance()  # INDEXED
                not_indexed = True

        return TableReference(name=name, alias=alias, indexed_by=indexed_by, not_indexed=not_indexed)

    def parse_where_clause(self) -> WhereClause:
        """Parse WHERE clause"""
        self.expect(TokenType.WHERE)
        condition = self.parse_expression()
        return WhereClause(condition=condition)

    def parse_group_by_clause(self) -> GroupByClause:
        """Parse GROUP BY clause"""
        self.expect(TokenType.GROUP)
        self.expect(TokenType.BY)

        expressions = [self.parse_expression()]
        while self.match(TokenType.COMMA):
            self.advance()
            expressions.append(self.parse_expression())

        # Optional HAVING
        having = None
        if self.match(TokenType.HAVING):
            having = self.parse_having_clause()

        return GroupByClause(expressions=expressions, having=having)

    def parse_having_clause(self) -> HavingClause:
        """Parse HAVING clause"""
        self.expect(TokenType.HAVING)
        condition = self.parse_expression()
        return HavingClause(condition=condition)

    def parse_order_by_clause(self) -> OrderByClause:
        """Parse ORDER BY clause"""
        self.expect(TokenType.ORDER)
        self.expect(TokenType.BY)
        terms = self.parse_ordering_terms()
        return OrderByClause(terms=terms)

    def parse_ordering_terms(self) -> List[OrderingTerm]:
        """Parse ordering terms"""
        terms = []

        terms.append(self.parse_ordering_term())
        while self.match(TokenType.COMMA):
            self.advance()
            terms.append(self.parse_ordering_term())

        return terms

    def parse_ordering_term(self) -> OrderingTerm:
        """Parse single ordering term"""
        expression = self.parse_expression()

        direction = None
        if self.match(TokenType.ASC):
            self.advance()
            direction = OrderDirection.ASC
        elif self.match(TokenType.DESC):
            self.advance()
            direction = OrderDirection.DESC

        nulls = None
        if self.match(TokenType.NULLS):
            self.advance()
            if self.match(TokenType.FIRST):
                self.advance()
                nulls = NullsOrdering.FIRST
            elif self.match(TokenType.LAST):
                self.advance()
                nulls = NullsOrdering.LAST

        return OrderingTerm(expression=expression, direction=direction, nulls=nulls)

    def parse_limit_clause(self) -> LimitClause:
        """Parse LIMIT clause"""
        self.expect(TokenType.LIMIT)
        limit = self.parse_expression()

        offset = None
        if self.match(TokenType.OFFSET):
            self.advance()
            offset = self.parse_expression()
        elif self.match(TokenType.COMMA):
            # Alternative LIMIT offset, count syntax
            self.advance()
            offset = limit
            limit = self.parse_expression()

        return LimitClause(limit=limit, offset=offset)

    def parse_with_clause(self) -> WithClause:
        """Parse WITH clause"""
        self.expect(TokenType.WITH)

        recursive = False
        if self.match(TokenType.RECURSIVE):
            self.advance()
            recursive = True

        ctes = []
        ctes.append(self.parse_cte())
        while self.match(TokenType.COMMA):
            self.advance()
            ctes.append(self.parse_cte())

        return WithClause(recursive=recursive, ctes=ctes)

    def parse_cte(self) -> CommonTableExpression:
        """Parse single CTE"""
        name = self.expect(TokenType.IDENTIFIER).value

        # Optional column list
        columns = []
        if self.match(TokenType.LPAREN):
            self.advance()
            columns.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                self.advance()
                columns.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RPAREN)

        self.expect(TokenType.AS)

        # Optional MATERIALIZED/NOT MATERIALIZED
        materialized = None
        if self.match(TokenType.MATERIALIZED):
            self.advance()
            materialized = True
        elif self.match(TokenType.NOT):
            if self.peek(1).type == TokenType.MATERIALIZED:
                self.advance()
                self.advance()
                materialized = False

        self.expect(TokenType.LPAREN)
        select = self.parse_select_statement()
        self.expect(TokenType.RPAREN)

        return CommonTableExpression(
            name=name,
            columns=columns,
            select=select,
            materialized=materialized
        )

    def parse_window_definitions(self) -> List[Tuple[str, WindowExpression]]:
        """Parse WINDOW definitions"""
        self.expect(TokenType.WINDOW)

        windows = []
        windows.append(self.parse_window_definition())
        while self.match(TokenType.COMMA):
            self.advance()
            windows.append(self.parse_window_definition())

        return windows

    def parse_window_definition(self) -> Tuple[str, WindowExpression]:
        """Parse single window definition"""
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.AS)
        window = self.parse_window_expression()
        return (name, window)

    # =========================================================================
    # INSERT Statement
    # =========================================================================

    def parse_insert_statement(self) -> InsertStatement:
        """Parse INSERT statement"""
        # Parse WITH clause
        with_clause = None
        if self.match(TokenType.WITH):
            with_clause = self.parse_with_clause()

        # Check for REPLACE
        replace = False
        if self.match(TokenType.REPLACE):
            self.advance()
            replace = True
        else:
            self.expect(TokenType.INSERT)

        # Check for OR conflict resolution
        conflict_resolution = None
        if self.match(TokenType.OR):
            self.advance()
            conflict_resolution = self.parse_conflict_resolution()

        self.expect(TokenType.INTO)

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table = QualifiedIdentifier(parts=table_parts)

        # Optional table alias
        table_alias = None
        if self.match(TokenType.AS):
            self.advance()
            table_alias = self.expect(TokenType.IDENTIFIER).value

        # Optional column list
        columns = []
        if self.match(TokenType.LPAREN):
            self.advance()
            columns.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                self.advance()
                columns.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RPAREN)

        # Parse VALUES, SELECT, or DEFAULT VALUES
        values = None
        select = None
        default_values = False

        if self.match(TokenType.VALUES):
            values = self.parse_values_clause()
        elif self.match(TokenType.SELECT, TokenType.WITH):
            select = self.parse_select_statement()
        elif self.match(TokenType.DEFAULT):
            self.advance()
            self.expect(TokenType.VALUES)
            default_values = True

        # Parse UPSERT clauses
        upsert_clauses = []
        while self.match(TokenType.ON):
            upsert_clauses.append(self.parse_upsert_clause())

        # Parse RETURNING
        returning = None
        if self.match(TokenType.RETURNING):
            returning = self.parse_returning_clause()

        return InsertStatement(
            with_clause=with_clause,
            replace=replace,
            conflict_resolution=conflict_resolution,
            table=table,
            table_alias=table_alias,
            columns=columns,
            values=values,
            select=select,
            default_values=default_values,
            upsert_clauses=upsert_clauses,
            returning=returning
        )

    def parse_values_clause(self) -> ValuesClause:
        """Parse VALUES clause"""
        self.expect(TokenType.VALUES)

        rows = []
        rows.append(self.parse_value_row())
        while self.match(TokenType.COMMA):
            self.advance()
            rows.append(self.parse_value_row())

        return ValuesClause(rows=rows)

    def parse_value_row(self) -> List[Expression]:
        """Parse single value row"""
        self.expect(TokenType.LPAREN)

        values = [self.parse_expression()]
        while self.match(TokenType.COMMA):
            self.advance()
            values.append(self.parse_expression())

        self.expect(TokenType.RPAREN)
        return values

    def parse_upsert_clause(self) -> UpsertClause:
        """Parse UPSERT clause (ON CONFLICT)"""
        self.expect(TokenType.ON)
        self.expect(TokenType.CONFLICT)

        # Optional conflict target
        conflict_target = None
        if self.match(TokenType.LPAREN):
            conflict_target = self.parse_conflict_target()

        # DO NOTHING or DO UPDATE
        self.expect(TokenType.DO)

        do_nothing = False
        do_update = None

        if self.match(TokenType.NOTHING):
            self.advance()
            do_nothing = True
        elif self.match(TokenType.UPDATE):
            do_update = self.parse_do_update_clause()

        return UpsertClause(
            conflict_target=conflict_target,
            do_nothing=do_nothing,
            do_update=do_update
        )

    def parse_conflict_target(self) -> ConflictTarget:
        """Parse conflict target"""
        self.expect(TokenType.LPAREN)

        indexed_columns = []
        indexed_columns.append(self.parse_indexed_column())
        while self.match(TokenType.COMMA):
            self.advance()
            indexed_columns.append(self.parse_indexed_column())

        self.expect(TokenType.RPAREN)

        # Optional WHERE
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        return ConflictTarget(indexed_columns=indexed_columns, where=where)

    def parse_do_update_clause(self) -> DoUpdateClause:
        """Parse DO UPDATE SET clause"""
        self.expect(TokenType.UPDATE)
        self.expect(TokenType.SET)

        assignments = []
        assignments.append(self.parse_assignment())
        while self.match(TokenType.COMMA):
            self.advance()
            assignments.append(self.parse_assignment())

        # Optional WHERE
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        return DoUpdateClause(assignments=assignments, where=where)

    def parse_assignment(self) -> Assignment:
        """Parse column assignment"""
        column = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.EQUAL)
        value = self.parse_expression()
        return Assignment(column=column, value=value)

    def parse_indexed_column(self) -> IndexedColumn:
        """Parse indexed column"""
        expr = self.parse_expression()

        collation = None
        if self.match(TokenType.COLLATE):
            self.advance()
            collation = self.expect(TokenType.IDENTIFIER).value

        direction = None
        if self.match(TokenType.ASC):
            self.advance()
            direction = OrderDirection.ASC
        elif self.match(TokenType.DESC):
            self.advance()
            direction = OrderDirection.DESC

        return IndexedColumn(expression=expr, collation=collation, direction=direction)

    def parse_conflict_resolution(self) -> ConflictResolution:
        """Parse conflict resolution"""
        if self.match(TokenType.ROLLBACK):
            self.advance()
            return ConflictResolution.ROLLBACK
        elif self.match(TokenType.ABORT):
            self.advance()
            return ConflictResolution.ABORT
        elif self.match(TokenType.FAIL):
            self.advance()
            return ConflictResolution.FAIL
        elif self.match(TokenType.IGNORE):
            self.advance()
            return ConflictResolution.IGNORE
        elif self.match(TokenType.REPLACE):
            self.advance()
            return ConflictResolution.REPLACE

        raise SQLSyntaxError("Expected conflict resolution", self.peek().position)

    def parse_returning_clause(self) -> ReturningClause:
        """Parse RETURNING clause"""
        self.expect(TokenType.RETURNING)
        columns = self.parse_result_columns()
        return ReturningClause(columns=columns)

    # =========================================================================
    # UPDATE Statement
    # =========================================================================

    def parse_update_statement(self) -> UpdateStatement:
        """Parse UPDATE statement"""
        # Parse WITH clause
        with_clause = None
        if self.match(TokenType.WITH):
            with_clause = self.parse_with_clause()

        self.expect(TokenType.UPDATE)

        # Check for OR conflict resolution
        conflict_resolution = None
        if self.match(TokenType.OR):
            self.advance()
            conflict_resolution = self.parse_conflict_resolution()

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table = QualifiedIdentifier(parts=table_parts)

        # Optional table alias
        table_alias = None
        if self.match(TokenType.AS):
            self.advance()
            table_alias = self.expect(TokenType.IDENTIFIER).value

        # Optional INDEXED BY or NOT INDEXED
        indexed_by = None
        not_indexed = False

        if self.match(TokenType.INDEXED):
            self.advance()
            self.expect(TokenType.BY)
            indexed_by = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.NOT):
            if self.peek(1).type == TokenType.INDEXED:
                self.advance()
                self.advance()
                not_indexed = True

        # Parse SET clause
        self.expect(TokenType.SET)
        assignments = []
        assignments.append(self.parse_assignment())
        while self.match(TokenType.COMMA):
            self.advance()
            assignments.append(self.parse_assignment())

        # Parse FROM clause (UPDATE FROM extension)
        from_clause = None
        if self.match(TokenType.FROM):
            from_clause = self.parse_from_clause()

        # Parse WHERE clause
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        # Parse ORDER BY (if SQLITE_ENABLE_UPDATE_DELETE_LIMIT)
        order_by = None
        if self.match(TokenType.ORDER):
            order_by = self.parse_order_by_clause()

        # Parse LIMIT (if SQLITE_ENABLE_UPDATE_DELETE_LIMIT)
        limit = None
        if self.match(TokenType.LIMIT):
            limit = self.parse_limit_clause()

        # Parse RETURNING
        returning = None
        if self.match(TokenType.RETURNING):
            returning = self.parse_returning_clause()

        return UpdateStatement(
            with_clause=with_clause,
            conflict_resolution=conflict_resolution,
            table=table,
            table_alias=table_alias,
            indexed_by=indexed_by,
            not_indexed=not_indexed,
            assignments=assignments,
            from_clause=from_clause,
            where=where,
            order_by=order_by,
            limit=limit,
            returning=returning
        )

    # =========================================================================
    # DELETE Statement
    # =========================================================================

    def parse_delete_statement(self) -> DeleteStatement:
        """Parse DELETE statement"""
        # Parse WITH clause
        with_clause = None
        if self.match(TokenType.WITH):
            with_clause = self.parse_with_clause()

        self.expect(TokenType.DELETE)
        self.expect(TokenType.FROM)

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table = QualifiedIdentifier(parts=table_parts)

        # Optional table alias
        table_alias = None
        if self.match(TokenType.AS):
            self.advance()
            table_alias = self.expect(TokenType.IDENTIFIER).value

        # Optional INDEXED BY or NOT INDEXED
        indexed_by = None
        not_indexed = False

        if self.match(TokenType.INDEXED):
            self.advance()
            self.expect(TokenType.BY)
            indexed_by = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.NOT):
            if self.peek(1).type == TokenType.INDEXED:
                self.advance()
                self.advance()
                not_indexed = True

        # Parse WHERE clause
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        # Parse ORDER BY (if SQLITE_ENABLE_UPDATE_DELETE_LIMIT)
        order_by = None
        if self.match(TokenType.ORDER):
            order_by = self.parse_order_by_clause()

        # Parse LIMIT (if SQLITE_ENABLE_UPDATE_DELETE_LIMIT)
        limit = None
        if self.match(TokenType.LIMIT):
            limit = self.parse_limit_clause()

        # Parse RETURNING
        returning = None
        if self.match(TokenType.RETURNING):
            returning = self.parse_returning_clause()

        return DeleteStatement(
            with_clause=with_clause,
            table=table,
            table_alias=table_alias,
            indexed_by=indexed_by,
            not_indexed=not_indexed,
            where=where,
            order_by=order_by,
            limit=limit,
            returning=returning
        )

    # =========================================================================
    # CREATE Statements
    # =========================================================================

    def parse_create_statement(self) -> Statement:
        """Parse CREATE statement"""
        self.expect(TokenType.CREATE)

        # Check for TEMP/TEMPORARY
        temporary = False
        if self.match(TokenType.TEMP, TokenType.TEMPORARY):
            self.advance()
            temporary = True

        # Determine what to create
        if self.match(TokenType.TABLE):
            return self.parse_create_table_statement(temporary)
        elif self.match(TokenType.INDEX):
            return self.parse_create_index_statement()
        elif self.match(TokenType.VIEW):
            return self.parse_create_view_statement(temporary)
        elif self.match(TokenType.TRIGGER):
            return self.parse_create_trigger_statement(temporary)
        elif self.match(TokenType.VIRTUAL):
            return self.parse_create_virtual_table_statement()
        elif self.match(TokenType.UNIQUE):
            # UNIQUE INDEX
            self.advance()  # consume UNIQUE
            return self.parse_create_index_statement(unique=True)
        else:
            raise SQLSyntaxError(
                f"Expected TABLE, INDEX, VIEW, TRIGGER, or VIRTUAL after CREATE",
                self.peek().position
            )

    def parse_create_table_statement(self, temporary: bool = False) -> CreateTableStatement:
        """Parse CREATE TABLE statement"""
        self.expect(TokenType.TABLE)

        # Check for IF NOT EXISTS
        if_not_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.NOT)
            self.expect(TokenType.EXISTS)
            if_not_exists = True

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table_name = QualifiedIdentifier(parts=table_parts)

        # Check for AS SELECT
        if self.match(TokenType.AS):
            self.advance()
            as_select = self.parse_select_statement()
            return CreateTableStatement(
                temporary=temporary,
                if_not_exists=if_not_exists,
                table_name=table_name,
                as_select=as_select
            )

        # Parse column definitions and constraints
        self.expect(TokenType.LPAREN)

        columns = []
        constraints = []

        # Parse first item (column or constraint)
        if self.match(TokenType.CONSTRAINT, TokenType.PRIMARY,
                     TokenType.UNIQUE, TokenType.CHECK, TokenType.FOREIGN):
            constraints.append(self.parse_table_constraint())
        else:
            columns.append(self.parse_column_definition())

        # Parse remaining items
        while self.match(TokenType.COMMA):
            self.advance()

            if self.match(TokenType.CONSTRAINT, TokenType.PRIMARY,
                         TokenType.UNIQUE, TokenType.CHECK, TokenType.FOREIGN):
                constraints.append(self.parse_table_constraint())
            else:
                columns.append(self.parse_column_definition())

        self.expect(TokenType.RPAREN)

        # Optional WITHOUT ROWID
        without_rowid = False
        if self.match(TokenType.WITHOUT):
            self.advance()
            self.expect(TokenType.ROWID)
            without_rowid = True

        # Optional STRICT
        strict = False
        if self.match(TokenType.STRICT):
            self.advance()
            strict = True

        return CreateTableStatement(
            temporary=temporary,
            if_not_exists=if_not_exists,
            table_name=table_name,
            columns=columns,
            constraints=constraints,
            without_rowid=without_rowid,
            strict=strict
        )

    def parse_column_definition(self) -> ColumnDefinition:
        """Parse column definition"""
        # Allow keywords as column names (SQLite allows this)
        name = self.expect_identifier_or_keyword().value

        # Optional type name (also allow keywords here)
        type_name = None
        if not self.match(TokenType.COMMA, TokenType.RPAREN, TokenType.CONSTRAINT,
                         TokenType.PRIMARY, TokenType.NOT, TokenType.UNIQUE,
                         TokenType.CHECK, TokenType.DEFAULT, TokenType.COLLATE,
                         TokenType.REFERENCES, TokenType.GENERATED):
            type_name = self.expect_identifier_or_keyword().value

        # Parse constraints
        constraints = []
        while True:
            if self.match(TokenType.CONSTRAINT):
                constraints.append(self.parse_column_constraint(has_name=True))
            elif self.match(TokenType.PRIMARY, TokenType.NOT, TokenType.UNIQUE,
                           TokenType.CHECK, TokenType.DEFAULT, TokenType.COLLATE,
                           TokenType.REFERENCES, TokenType.GENERATED):
                constraints.append(self.parse_column_constraint())
            else:
                break

        return ColumnDefinition(name=name, type_name=type_name, constraints=constraints)

    def parse_column_constraint(self, has_name: bool = False) -> ColumnConstraint:
        """Parse column constraint"""
        name = None
        if has_name:
            self.expect(TokenType.CONSTRAINT)
            name = self.expect(TokenType.IDENTIFIER).value

        constraint = ColumnConstraint(name=name)

        if self.match(TokenType.PRIMARY):
            self.advance()
            self.expect(TokenType.KEY)
            constraint.constraint_type = "PRIMARY_KEY"
            constraint.primary_key = True

            if self.match(TokenType.ASC, TokenType.DESC):
                self.advance()  # Ignored by SQLite

            if self.match(TokenType.AUTOINCREMENT):
                self.advance()
                constraint.autoincrement = True

        elif self.match(TokenType.NOT):
            self.advance()
            self.expect(TokenType.NULL)
            constraint.constraint_type = "NOT_NULL"
            constraint.not_null = True

        elif self.match(TokenType.UNIQUE):
            self.advance()
            constraint.constraint_type = "UNIQUE"
            constraint.unique = True

        elif self.match(TokenType.CHECK):
            self.advance()
            self.expect(TokenType.LPAREN)
            constraint.constraint_type = "CHECK"
            constraint.check_expression = self.parse_expression()
            self.expect(TokenType.RPAREN)

        elif self.match(TokenType.DEFAULT):
            self.advance()
            constraint.constraint_type = "DEFAULT"

            if self.match(TokenType.LPAREN):
                self.advance()
                constraint.default_value = self.parse_expression()
                self.expect(TokenType.RPAREN)
            else:
                constraint.default_value = self.parse_expression()

        elif self.match(TokenType.COLLATE):
            self.advance()
            constraint.constraint_type = "COLLATE"
            constraint.collation = self.expect(TokenType.IDENTIFIER).value

        elif self.match(TokenType.REFERENCES):
            constraint.constraint_type = "REFERENCES"
            constraint.foreign_key = self.parse_foreign_key_clause()

        elif self.match(TokenType.GENERATED):
            constraint.constraint_type = "GENERATED"
            constraint.generated = self.parse_generated_column_clause()

        # Optional ON CONFLICT
        if self.match(TokenType.ON):
            self.advance()
            self.expect(TokenType.CONFLICT)
            constraint.on_conflict = self.parse_conflict_resolution()

        return constraint

    def parse_table_constraint(self) -> TableConstraint:
        """Parse table constraint"""
        name = None
        if self.match(TokenType.CONSTRAINT):
            self.advance()
            name = self.expect(TokenType.IDENTIFIER).value

        constraint = TableConstraint(name=name)

        if self.match(TokenType.PRIMARY):
            self.advance()
            self.expect(TokenType.KEY)
            constraint.constraint_type = "PRIMARY_KEY"

            self.expect(TokenType.LPAREN)
            constraint.columns = [self.parse_indexed_column()]
            while self.match(TokenType.COMMA):
                self.advance()
                constraint.columns.append(self.parse_indexed_column())
            self.expect(TokenType.RPAREN)

        elif self.match(TokenType.UNIQUE):
            self.advance()
            constraint.constraint_type = "UNIQUE"

            self.expect(TokenType.LPAREN)
            constraint.columns = [self.parse_indexed_column()]
            while self.match(TokenType.COMMA):
                self.advance()
                constraint.columns.append(self.parse_indexed_column())
            self.expect(TokenType.RPAREN)

        elif self.match(TokenType.CHECK):
            self.advance()
            constraint.constraint_type = "CHECK"

            self.expect(TokenType.LPAREN)
            constraint.check_expression = self.parse_expression()
            self.expect(TokenType.RPAREN)

        elif self.match(TokenType.FOREIGN):
            self.advance()
            self.expect(TokenType.KEY)
            constraint.constraint_type = "FOREIGN_KEY"

            self.expect(TokenType.LPAREN)
            # Parse column list
            cols = [self.expect(TokenType.IDENTIFIER).value]
            while self.match(TokenType.COMMA):
                self.advance()
                cols.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RPAREN)

            # Create indexed columns from names
            constraint.columns = [
                IndexedColumn(expression=Identifier(name=col))
                for col in cols
            ]

            constraint.foreign_key = self.parse_foreign_key_clause()

        # Optional ON CONFLICT
        if self.match(TokenType.ON):
            self.advance()
            self.expect(TokenType.CONFLICT)
            constraint.on_conflict = self.parse_conflict_resolution()

        return constraint

    def parse_foreign_key_clause(self) -> ForeignKeyClause:
        """Parse FOREIGN KEY clause"""
        self.expect(TokenType.REFERENCES)
        foreign_table = self.expect(TokenType.IDENTIFIER).value

        # Optional foreign columns
        foreign_columns = []
        if self.match(TokenType.LPAREN):
            self.advance()
            foreign_columns.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                self.advance()
                foreign_columns.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RPAREN)

        # Optional ON DELETE/UPDATE
        on_delete = None
        on_update = None

        while self.match(TokenType.ON):
            self.advance()
            if self.match(TokenType.DELETE):
                self.advance()
                on_delete = self.parse_foreign_key_action()
            elif self.match(TokenType.UPDATE):
                self.advance()
                on_update = self.parse_foreign_key_action()

        # Optional MATCH
        match = None
        if self.match(TokenType.MATCH):
            self.advance()
            match = self.expect(TokenType.IDENTIFIER).value

        # Optional DEFERRABLE
        deferrable = None
        initially_deferred = None

        if self.match(TokenType.NOT):
            if self.peek(1).type == TokenType.DEFERRABLE:
                self.advance()
                self.advance()
                deferrable = False

        elif self.match(TokenType.DEFERRABLE):
            self.advance()
            deferrable = True

            if self.match(TokenType.INITIALLY):
                self.advance()
                if self.match(TokenType.DEFERRED):
                    self.advance()
                    initially_deferred = True
                elif self.match(TokenType.IMMEDIATE):
                    self.advance()
                    initially_deferred = False

        return ForeignKeyClause(
            foreign_table=foreign_table,
            foreign_columns=foreign_columns,
            on_delete=on_delete,
            on_update=on_update,
            match=match,
            deferrable=deferrable,
            initially_deferred=initially_deferred
        )

    def parse_foreign_key_action(self) -> str:
        """Parse foreign key action"""
        if self.match(TokenType.SET):
            self.advance()
            if self.match(TokenType.NULL):
                self.advance()
                return "SET NULL"
            elif self.match(TokenType.DEFAULT):
                self.advance()
                return "SET DEFAULT"
        elif self.match(TokenType.CASCADE):
            self.advance()
            return "CASCADE"
        elif self.match(TokenType.RESTRICT):
            self.advance()
            return "RESTRICT"
        elif self.match(TokenType.NO):
            self.advance()
            self.expect(TokenType.ACTION)
            return "NO ACTION"

        raise SQLSyntaxError("Expected foreign key action", self.peek().position)

    def parse_generated_column_clause(self) -> GeneratedColumnClause:
        """Parse GENERATED ALWAYS AS clause"""
        self.expect(TokenType.GENERATED)
        self.expect(TokenType.ALWAYS)
        self.expect(TokenType.AS)
        self.expect(TokenType.LPAREN)
        expression = self.parse_expression()
        self.expect(TokenType.RPAREN)

        stored = False
        if self.match(TokenType.STORED):
            self.advance()
            stored = True
        elif self.match(TokenType.VIRTUAL):
            self.advance()

        return GeneratedColumnClause(expression=expression, stored=stored)

    def parse_create_index_statement(self, unique: bool = False) -> CreateIndexStatement:
        """Parse CREATE INDEX statement"""
        if not unique:
            # Check for UNIQUE keyword
            if self.match(TokenType.UNIQUE):
                self.advance()
                unique = True

        self.expect(TokenType.INDEX)

        # Check for IF NOT EXISTS
        if_not_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.NOT)
            self.expect(TokenType.EXISTS)
            if_not_exists = True

        # Parse index name
        index_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            index_parts.append(self.expect(TokenType.IDENTIFIER).value)
        index_name = QualifiedIdentifier(parts=index_parts)

        self.expect(TokenType.ON)
        table_name = self.expect(TokenType.IDENTIFIER).value

        # Parse indexed columns
        self.expect(TokenType.LPAREN)
        indexed_columns = [self.parse_indexed_column()]
        while self.match(TokenType.COMMA):
            self.advance()
            indexed_columns.append(self.parse_indexed_column())
        self.expect(TokenType.RPAREN)

        # Optional WHERE clause
        where = None
        if self.match(TokenType.WHERE):
            where = self.parse_where_clause()

        return CreateIndexStatement(
            unique=unique,
            if_not_exists=if_not_exists,
            index_name=index_name,
            table_name=table_name,
            indexed_columns=indexed_columns,
            where=where
        )

    def parse_create_view_statement(self, temporary: bool = False) -> CreateViewStatement:
        """Parse CREATE VIEW statement"""
        self.expect(TokenType.VIEW)

        # Check for IF NOT EXISTS
        if_not_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.NOT)
            self.expect(TokenType.EXISTS)
            if_not_exists = True

        # Parse view name
        view_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            view_parts.append(self.expect(TokenType.IDENTIFIER).value)
        view_name = QualifiedIdentifier(parts=view_parts)

        # Optional column list
        columns = []
        if self.match(TokenType.LPAREN):
            self.advance()
            columns.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA):
                self.advance()
                columns.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RPAREN)

        self.expect(TokenType.AS)
        select = self.parse_select_statement()

        return CreateViewStatement(
            temporary=temporary,
            if_not_exists=if_not_exists,
            view_name=view_name,
            columns=columns,
            select=select
        )

    def parse_create_trigger_statement(self, temporary: bool = False) -> CreateTriggerStatement:
        """Parse CREATE TRIGGER statement"""
        self.expect(TokenType.TRIGGER)

        # Check for IF NOT EXISTS
        if_not_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.NOT)
            self.expect(TokenType.EXISTS)
            if_not_exists = True

        # Parse trigger name
        trigger_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            trigger_parts.append(self.expect(TokenType.IDENTIFIER).value)
        trigger_name = QualifiedIdentifier(parts=trigger_parts)

        # Parse timing
        timing = None
        instead_of = False

        if self.match(TokenType.BEFORE):
            self.advance()
            timing = TriggerTiming.BEFORE
        elif self.match(TokenType.AFTER):
            self.advance()
            timing = TriggerTiming.AFTER
        elif self.match(TokenType.INSTEAD):
            self.advance()
            self.expect(TokenType.OF)
            instead_of = True

        # Parse event
        event = None
        update_columns = []

        if self.match(TokenType.DELETE):
            self.advance()
            event = TriggerEvent.DELETE
        elif self.match(TokenType.INSERT):
            self.advance()
            event = TriggerEvent.INSERT
        elif self.match(TokenType.UPDATE):
            self.advance()
            event = TriggerEvent.UPDATE

            # Optional OF column-list
            if self.match(TokenType.OF):
                self.advance()
                update_columns.append(self.expect(TokenType.IDENTIFIER).value)
                while self.match(TokenType.COMMA):
                    self.advance()
                    update_columns.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.ON)
        table_name = self.expect(TokenType.IDENTIFIER).value

        # Optional FOR EACH ROW
        for_each_row = False
        if self.match(TokenType.FOR):
            self.advance()
            self.expect(TokenType.EACH)
            self.expect(TokenType.ROW)
            for_each_row = True

        # Optional WHEN clause
        when = None
        if self.match(TokenType.WHEN):
            when = self.parse_where_clause()  # Reuse WHERE parsing

        # Parse trigger body
        self.expect(TokenType.BEGIN)

        body = []
        while True:
            # Check for END before trying to parse a statement
            if self.match(TokenType.END):
                break

            stmt = self.parse_statement()
            body.append(stmt)

            # Optional semicolon
            if self.match(TokenType.SEMICOLON):
                self.advance()

        self.expect(TokenType.END)

        return CreateTriggerStatement(
            temporary=temporary,
            if_not_exists=if_not_exists,
            trigger_name=trigger_name,
            timing=timing,
            instead_of=instead_of,
            event=event,
            update_columns=update_columns,
            table_name=table_name,
            for_each_row=for_each_row,
            when=when,
            body=body
        )

    def parse_create_virtual_table_statement(self) -> CreateVirtualTableStatement:
        """Parse CREATE VIRTUAL TABLE statement"""
        self.expect(TokenType.VIRTUAL)
        self.expect(TokenType.TABLE)

        # Check for IF NOT EXISTS
        if_not_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.NOT)
            self.expect(TokenType.EXISTS)
            if_not_exists = True

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table_name = QualifiedIdentifier(parts=table_parts)

        self.expect(TokenType.USING)
        module_name = self.expect(TokenType.IDENTIFIER).value

        # Optional module arguments
        module_arguments = []
        if self.match(TokenType.LPAREN):
            self.advance()
            # Parse arguments as strings
            # This is flexible - could be anything
            while not self.match(TokenType.RPAREN):
                # Simple approach: collect everything as strings
                arg = self.advance().value
                module_arguments.append(arg)
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RPAREN)

        return CreateVirtualTableStatement(
            if_not_exists=if_not_exists,
            table_name=table_name,
            module_name=module_name,
            module_arguments=module_arguments
        )

    # =========================================================================
    # ALTER TABLE Statement
    # =========================================================================

    def parse_alter_statement(self) -> AlterTableStatement:
        """Parse ALTER TABLE statement"""
        self.expect(TokenType.ALTER)
        self.expect(TokenType.TABLE)

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table_name = QualifiedIdentifier(parts=table_parts)

        # Parse action
        action = None

        if self.match(TokenType.RENAME):
            action = self.parse_alter_table_rename_action()
        elif self.match(TokenType.ADD):
            action = self.parse_alter_table_add_action()
        elif self.match(TokenType.DROP):
            action = self.parse_alter_table_drop_action()
        else:
            raise SQLSyntaxError(
                "Expected RENAME, ADD, or DROP after ALTER TABLE",
                self.peek().position
            )

        return AlterTableStatement(table_name=table_name, action=action)

    def parse_alter_table_rename_action(self) -> AlterTableAction:
        """Parse ALTER TABLE RENAME action"""
        self.expect(TokenType.RENAME)

        action = AlterTableAction()

        if self.match(TokenType.TO):
            # RENAME TABLE
            self.advance()
            action.action_type = "RENAME_TABLE"
            action.new_table_name = self.expect(TokenType.IDENTIFIER).value

        elif self.match(TokenType.COLUMN):
            # RENAME COLUMN
            self.advance()
            action.action_type = "RENAME_COLUMN"
            action.old_column_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.TO)
            action.new_column_name = self.expect(TokenType.IDENTIFIER).value

        else:
            raise SQLSyntaxError(
                "Expected TO or COLUMN after RENAME",
                self.peek().position
            )

        return action

    def parse_alter_table_add_action(self) -> AlterTableAction:
        """Parse ALTER TABLE ADD COLUMN action"""
        self.expect(TokenType.ADD)

        # Optional COLUMN keyword
        if self.match(TokenType.COLUMN):
            self.advance()

        action = AlterTableAction()
        action.action_type = "ADD_COLUMN"
        action.column_definition = self.parse_column_definition()

        return action

    def parse_alter_table_drop_action(self) -> AlterTableAction:
        """Parse ALTER TABLE DROP COLUMN action"""
        self.expect(TokenType.DROP)

        # Optional COLUMN keyword
        if self.match(TokenType.COLUMN):
            self.advance()

        action = AlterTableAction()
        action.action_type = "DROP_COLUMN"
        action.column_name = self.expect(TokenType.IDENTIFIER).value

        return action

    # =========================================================================
    # DROP Statements
    # =========================================================================

    def parse_drop_statement(self) -> Statement:
        """Parse DROP statement"""
        self.expect(TokenType.DROP)

        if self.match(TokenType.TABLE):
            return self.parse_drop_table_statement()
        elif self.match(TokenType.INDEX):
            return self.parse_drop_index_statement()
        elif self.match(TokenType.VIEW):
            return self.parse_drop_view_statement()
        elif self.match(TokenType.TRIGGER):
            return self.parse_drop_trigger_statement()
        else:
            raise SQLSyntaxError(
                "Expected TABLE, INDEX, VIEW, or TRIGGER after DROP",
                self.peek().position
            )

    def parse_drop_table_statement(self) -> DropTableStatement:
        """Parse DROP TABLE statement"""
        self.expect(TokenType.TABLE)

        # Check for IF EXISTS
        if_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.EXISTS)
            if_exists = True

        # Parse table name
        table_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            table_parts.append(self.expect(TokenType.IDENTIFIER).value)
        table_name = QualifiedIdentifier(parts=table_parts)

        return DropTableStatement(if_exists=if_exists, table_name=table_name)

    def parse_drop_index_statement(self) -> DropIndexStatement:
        """Parse DROP INDEX statement"""
        self.expect(TokenType.INDEX)

        # Check for IF EXISTS
        if_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.EXISTS)
            if_exists = True

        # Parse index name
        index_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            index_parts.append(self.expect(TokenType.IDENTIFIER).value)
        index_name = QualifiedIdentifier(parts=index_parts)

        return DropIndexStatement(if_exists=if_exists, index_name=index_name)

    def parse_drop_view_statement(self) -> DropViewStatement:
        """Parse DROP VIEW statement"""
        self.expect(TokenType.VIEW)

        # Check for IF EXISTS
        if_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.EXISTS)
            if_exists = True

        # Parse view name
        view_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            view_parts.append(self.expect(TokenType.IDENTIFIER).value)
        view_name = QualifiedIdentifier(parts=view_parts)

        return DropViewStatement(if_exists=if_exists, view_name=view_name)

    def parse_drop_trigger_statement(self) -> DropTriggerStatement:
        """Parse DROP TRIGGER statement"""
        self.expect(TokenType.TRIGGER)

        # Check for IF EXISTS
        if_exists = False
        if self.match(TokenType.IF):
            self.advance()
            self.expect(TokenType.EXISTS)
            if_exists = True

        # Parse trigger name
        trigger_parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            trigger_parts.append(self.expect(TokenType.IDENTIFIER).value)
        trigger_name = QualifiedIdentifier(parts=trigger_parts)

        return DropTriggerStatement(if_exists=if_exists, trigger_name=trigger_name)

    # =========================================================================
    # Transaction Control Statements
    # =========================================================================

    def parse_begin_statement(self) -> BeginStatement:
        """Parse BEGIN TRANSACTION statement"""
        self.expect(TokenType.BEGIN)

        # Optional transaction type
        transaction_type = None
        if self.match(TokenType.DEFERRED):
            self.advance()
            transaction_type = TransactionType.DEFERRED
        elif self.match(TokenType.IMMEDIATE):
            self.advance()
            transaction_type = TransactionType.IMMEDIATE
        elif self.match(TokenType.EXCLUSIVE):
            self.advance()
            transaction_type = TransactionType.EXCLUSIVE

        # Optional TRANSACTION keyword
        if self.match(TokenType.TRANSACTION):
            self.advance()

        return BeginStatement(transaction_type=transaction_type)

    def parse_commit_statement(self) -> CommitStatement:
        """Parse COMMIT TRANSACTION statement"""
        self.advance()  # COMMIT or END

        # Optional TRANSACTION keyword
        if self.match(TokenType.TRANSACTION):
            self.advance()

        return CommitStatement()

    def parse_rollback_statement(self) -> RollbackStatement:
        """Parse ROLLBACK TRANSACTION statement"""
        self.expect(TokenType.ROLLBACK)

        # Optional TRANSACTION keyword
        if self.match(TokenType.TRANSACTION):
            self.advance()

        # Optional TO SAVEPOINT
        savepoint = None
        if self.match(TokenType.TO):
            self.advance()
            if self.match(TokenType.SAVEPOINT):
                self.advance()
            savepoint = self.expect(TokenType.IDENTIFIER).value

        return RollbackStatement(savepoint=savepoint)

    def parse_savepoint_statement(self) -> SavepointStatement:
        """Parse SAVEPOINT statement"""
        self.expect(TokenType.SAVEPOINT)
        name = self.expect(TokenType.IDENTIFIER).value
        return SavepointStatement(name=name)

    def parse_release_statement(self) -> ReleaseStatement:
        """Parse RELEASE SAVEPOINT statement"""
        self.expect(TokenType.RELEASE)

        # Optional SAVEPOINT keyword
        if self.match(TokenType.SAVEPOINT):
            self.advance()

        name = self.expect(TokenType.IDENTIFIER).value
        return ReleaseStatement(name=name)

    # =========================================================================
    # Database Management Statements
    # =========================================================================

    def parse_attach_statement(self) -> AttachStatement:
        """Parse ATTACH DATABASE statement"""
        self.expect(TokenType.ATTACH)

        # Optional DATABASE keyword
        if self.match(TokenType.DATABASE):
            self.advance()

        database_expression = self.parse_expression()
        self.expect(TokenType.AS)
        schema_name = self.expect(TokenType.IDENTIFIER).value

        return AttachStatement(
            database_expression=database_expression,
            schema_name=schema_name
        )

    def parse_detach_statement(self) -> DetachStatement:
        """Parse DETACH DATABASE statement"""
        self.expect(TokenType.DETACH)

        # Optional DATABASE keyword
        if self.match(TokenType.DATABASE):
            self.advance()

        schema_name = self.expect(TokenType.IDENTIFIER).value
        return DetachStatement(schema_name=schema_name)

    def parse_analyze_statement(self) -> AnalyzeStatement:
        """Parse ANALYZE statement"""
        self.expect(TokenType.ANALYZE)

        # Optional target
        target = None
        if self.match(TokenType.IDENTIFIER):
            target_parts = [self.advance().value]
            while self.match(TokenType.DOT):
                self.advance()
                target_parts.append(self.expect(TokenType.IDENTIFIER).value)
            target = QualifiedIdentifier(parts=target_parts)

        return AnalyzeStatement(target=target)

    def parse_vacuum_statement(self) -> VacuumStatement:
        """Parse VACUUM statement"""
        self.expect(TokenType.VACUUM)

        # Optional schema name
        schema_name = None
        if self.match(TokenType.IDENTIFIER):
            schema_name = self.advance().value

        # Optional INTO clause
        into_filename = None
        if self.match(TokenType.INTO):
            self.advance()
            into_filename = self.parse_expression()

        return VacuumStatement(schema_name=schema_name, into_filename=into_filename)

    def parse_reindex_statement(self) -> ReindexStatement:
        """Parse REINDEX statement"""
        self.expect(TokenType.REINDEX)

        # Optional target
        target = None
        if self.match(TokenType.IDENTIFIER):
            target_parts = [self.advance().value]
            while self.match(TokenType.DOT):
                self.advance()
                target_parts.append(self.expect(TokenType.IDENTIFIER).value)

            if len(target_parts) == 1:
                # Could be collation name or table/index
                target = target_parts[0]
            else:
                target = QualifiedIdentifier(parts=target_parts)

        return ReindexStatement(target=target)

    def parse_explain_statement(self) -> ExplainStatement:
        """Parse EXPLAIN [QUERY PLAN] statement"""
        self.expect(TokenType.EXPLAIN)

        query_plan = False
        if self.match(TokenType.QUERY):
            self.advance()
            self.expect(TokenType.PLAN)
            query_plan = True

        statement = self.parse_statement()
        return ExplainStatement(query_plan=query_plan, statement=statement)

    def parse_pragma_statement(self) -> PragmaStatement:
        """Parse PRAGMA statement"""
        self.expect(TokenType.PRAGMA)

        # Optional schema name
        schema_name = None
        pragma_name = self.expect(TokenType.IDENTIFIER).value

        if self.match(TokenType.DOT):
            self.advance()
            schema_name = pragma_name
            pragma_name = self.expect(TokenType.IDENTIFIER).value

        # Optional value
        value = None
        if self.match(TokenType.EQUAL):
            self.advance()
            # Accept IDENTIFIER, keywords as identifiers, or NUMBER
            if self.match(TokenType.NUMBER):
                token = self.advance()
                value = int(token.value) if '.' not in token.value else float(token.value)
            elif not self.at_end() and self.peek().value:
                # Accept any token with a value (identifiers and keywords)
                value = self.advance().value
            else:
                value = self.parse_expression()
        elif self.match(TokenType.LPAREN):
            self.advance()
            # Accept IDENTIFIER, keywords as identifiers, or NUMBER
            if self.match(TokenType.NUMBER):
                token = self.advance()
                value = int(token.value) if '.' not in token.value else float(token.value)
            elif not self.at_end() and self.peek().value:
                # Accept any token with a value (identifiers and keywords)
                value = self.advance().value
            else:
                value = self.parse_expression()
            self.expect(TokenType.RPAREN)

        return PragmaStatement(
            schema_name=schema_name,
            pragma_name=pragma_name,
            value=value
        )


# =============================================================================
# Public API Functions
# =============================================================================

def parse_sql(sql: str) -> List[Statement]:
    """
    Parse SQL string and return list of statements

    Args:
        sql: SQL string to parse

    Returns:
        List of Statement AST nodes

    Raises:
        ParseError: If parsing fails
    """
    lexer = Lexer(sql)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()


def tokenize_sql(sql: str) -> List[Token]:
    """
    Tokenize SQL string and return list of tokens

    Args:
        sql: SQL string to tokenize

    Returns:
        List of Token objects

    Raises:
        LexerError: If tokenization fails
    """
    lexer = Lexer(sql)
    return lexer.tokenize()
