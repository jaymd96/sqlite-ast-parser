"""
SQLite SQL Lexer (Tokenizer)

Mode-driven tokenizer that converts SQL text into tokens with position tracking.
Follows the Scanner-Buffer mental model from lexer+parser_mental_model.md
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto

from .utils import TokenType, KEYWORDS, get_keyword_token_type
from .ast_nodes import Position, Span
from .errors import LexerError, InvalidTokenError


class LexerMode(Enum):
    """Lexer modes for context-sensitive tokenization"""
    NORMAL = auto()
    STRING_SINGLE = auto()
    STRING_DOUBLE = auto()
    BLOCK_COMMENT = auto()
    LINE_COMMENT = auto()
    BRACKET_IDENTIFIER = auto()
    BACKTICK_IDENTIFIER = auto()


@dataclass
class Token:
    """Token with type, value, and position information"""
    type: TokenType
    value: str
    position: Position
    span: Span

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, {self.position})"


class Lexer:
    """
    SQLite SQL Lexer

    Converts SQL text into a stream of tokens using a mode-driven
    scanner-buffer approach.
    """

    def __init__(self, sql: str):
        self.sql = sql
        self.pos = 0  # current position
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

        # Buffer for building current token
        self.buffer = ""
        self.buffer_start_pos = Position(1, 1, 0)

        # Mode stack for nested contexts
        self.mode_stack: List[LexerMode] = [LexerMode.NORMAL]

    def current_mode(self) -> LexerMode:
        """Get current lexer mode"""
        return self.mode_stack[-1]

    def push_mode(self, mode: LexerMode):
        """Push new mode onto stack"""
        self.mode_stack.append(mode)

    def pop_mode(self):
        """Pop mode from stack"""
        if len(self.mode_stack) > 1:
            self.mode_stack.pop()

    def at_end(self) -> bool:
        """Check if at end of input"""
        return self.pos >= len(self.sql)

    def peek(self, offset: int = 0) -> Optional[str]:
        """Look ahead at character without consuming"""
        pos = self.pos + offset
        if pos < len(self.sql):
            return self.sql[pos]
        return None

    def peek_string(self, length: int) -> str:
        """Look ahead at multiple characters"""
        return self.sql[self.pos:self.pos + length]

    def advance(self) -> Optional[str]:
        """Consume and return current character"""
        if self.at_end():
            return None

        char = self.sql[self.pos]
        self.buffer += char
        self.pos += 1

        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def skip(self) -> Optional[str]:
        """Consume character without adding to buffer"""
        if self.at_end():
            return None

        char = self.sql[self.pos]
        self.pos += 1

        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def current_position(self) -> Position:
        """Get current position"""
        return Position(self.line, self.column, self.pos)

    def emit(self, token_type: TokenType, value: Optional[str] = None) -> Token:
        """Emit token with position info"""
        if value is None:
            value = self.buffer

        span = Span(self.buffer_start_pos, self.current_position())
        token = Token(token_type, value, self.buffer_start_pos, span)
        self.tokens.append(token)

        # Reset buffer for next token
        self.buffer = ""
        self.buffer_start_pos = self.current_position()

        return token

    def error(self, message: str):
        """Raise lexer error"""
        raise LexerError(message, self.current_position(), sql=self.sql)

    def tokenize(self) -> List[Token]:
        """Tokenize entire SQL string"""
        while not self.at_end():
            mode = self.current_mode()

            if mode == LexerMode.NORMAL:
                self.lex_normal()
            elif mode == LexerMode.STRING_SINGLE:
                self.lex_string_single()
            elif mode == LexerMode.STRING_DOUBLE:
                self.lex_string_double()
            elif mode == LexerMode.BLOCK_COMMENT:
                self.lex_block_comment()
            elif mode == LexerMode.LINE_COMMENT:
                self.lex_line_comment()
            elif mode == LexerMode.BRACKET_IDENTIFIER:
                self.lex_bracket_identifier()
            elif mode == LexerMode.BACKTICK_IDENTIFIER:
                self.lex_backtick_identifier()

        # Emit EOF token
        self.emit(TokenType.EOF, "")
        return self.tokens

    def lex_normal(self):
        """Lex in normal mode"""
        char = self.peek()

        # Skip whitespace
        if char in ' \t\n\r':
            self.skip()
            return

        # Line comment --
        if char == '-' and self.peek(1) == '-':
            self.skip()  # first -
            self.skip()  # second -
            self.push_mode(LexerMode.LINE_COMMENT)
            return

        # Block comment /*
        if char == '/' and self.peek(1) == '*':
            self.skip()  # /
            self.skip()  # *
            self.push_mode(LexerMode.BLOCK_COMMENT)
            return

        # String literal '
        if char == "'":
            self.skip()  # skip opening quote
            self.push_mode(LexerMode.STRING_SINGLE)
            return

        # Identifier or string "
        if char == '"':
            self.skip()  # skip opening quote
            self.push_mode(LexerMode.STRING_DOUBLE)
            return

        # Bracket identifier [
        if char == '[':
            self.skip()  # skip opening bracket
            self.push_mode(LexerMode.BRACKET_IDENTIFIER)
            return

        # Backtick identifier `
        if char == '`':
            self.skip()  # skip opening backtick
            self.push_mode(LexerMode.BACKTICK_IDENTIFIER)
            return

        # Numbers
        if char.isdigit() or (char == '.' and self.peek(1) and self.peek(1).isdigit()):
            self.lex_number()
            return

        # BLOB literal X'hex'
        if char.upper() == 'X' and self.peek(1) == "'":
            self.lex_blob()
            return

        # Identifiers and keywords
        if char.isalpha() or char == '_':
            self.lex_identifier_or_keyword()
            return

        # Parameters
        if char in '?:@$':
            self.lex_parameter()
            return

        # Operators and punctuation
        self.lex_operator()

    def lex_string_single(self):
        """Lex single-quoted string"""
        while not self.at_end():
            char = self.peek()

            if char == "'":
                # Check for escaped quote ''
                if self.peek(1) == "'":
                    self.advance()  # first '
                    self.advance()  # second '
                else:
                    # End of string
                    value = self.buffer
                    self.skip()  # closing quote
                    self.emit(TokenType.STRING, value)
                    self.pop_mode()
                    return
            else:
                self.advance()

        self.error("Unterminated string literal")

    def lex_string_double(self):
        """Lex double-quoted identifier"""
        while not self.at_end():
            char = self.peek()

            if char == '"':
                # Check for escaped quote ""
                if self.peek(1) == '"':
                    self.advance()  # first "
                    self.advance()  # second "
                else:
                    # End of identifier
                    value = self.buffer
                    self.skip()  # closing quote
                    self.emit(TokenType.IDENTIFIER, value)
                    self.pop_mode()
                    return
            else:
                self.advance()

        self.error("Unterminated quoted identifier")

    def lex_bracket_identifier(self):
        """Lex bracket identifier"""
        while not self.at_end():
            char = self.peek()

            if char == ']':
                value = self.buffer
                self.skip()  # closing bracket
                self.emit(TokenType.IDENTIFIER, value)
                self.pop_mode()
                return
            else:
                self.advance()

        self.error("Unterminated bracket identifier")

    def lex_backtick_identifier(self):
        """Lex backtick identifier"""
        while not self.at_end():
            char = self.peek()

            if char == '`':
                value = self.buffer
                self.skip()  # closing backtick
                self.emit(TokenType.IDENTIFIER, value)
                self.pop_mode()
                return
            else:
                self.advance()

        self.error("Unterminated backtick identifier")

    def lex_line_comment(self):
        """Lex line comment until newline"""
        while not self.at_end():
            char = self.peek()
            if char == '\n':
                self.skip()
                self.pop_mode()
                return
            else:
                self.skip()

        # EOF ends comment
        self.pop_mode()

    def lex_block_comment(self):
        """Lex block comment until */"""
        while not self.at_end():
            if self.peek() == '*' and self.peek(1) == '/':
                self.skip()  # *
                self.skip()  # /
                self.pop_mode()
                return
            else:
                self.skip()

        self.error("Unterminated block comment")

    def lex_number(self):
        """Lex numeric literal"""
        # Handle optional leading dot for .123
        if self.peek() == '.':
            self.advance()

        # Integer part
        while not self.at_end() and self.peek().isdigit():
            self.advance()

        # Decimal part
        if not self.at_end() and self.peek() == '.' and self.peek(1) and self.peek(1).isdigit():
            self.advance()  # .
            while not self.at_end() and self.peek().isdigit():
                self.advance()

        # Exponent part
        if not self.at_end() and self.peek() in 'eE':
            self.advance()  # e or E
            if not self.at_end() and self.peek() in '+-':
                self.advance()  # sign
            while not self.at_end() and self.peek().isdigit():
                self.advance()

        self.emit(TokenType.NUMBER)

    def lex_blob(self):
        """Lex BLOB literal X'hex'"""
        self.advance()  # X
        self.skip()     # '

        # Read hex digits
        hex_digits = ""
        while not self.at_end():
            char = self.peek()
            if char == "'":
                self.buffer = f"X'{hex_digits}'"
                self.skip()  # closing '
                self.emit(TokenType.BLOB, hex_digits)
                return
            elif char in '0123456789abcdefABCDEF':
                hex_digits += char
                self.skip()
            else:
                self.error(f"Invalid character in BLOB literal: {char}")

        self.error("Unterminated BLOB literal")

    def lex_identifier_or_keyword(self):
        """Lex identifier or keyword"""
        while not self.at_end():
            char = self.peek()
            if char.isalnum() or char == '_':
                self.advance()
            else:
                break

        word = self.buffer
        token_type = get_keyword_token_type(word)
        self.emit(token_type)

    def lex_parameter(self):
        """Lex parameter placeholder"""
        prefix = self.advance()  # ?, :, @, or $

        if prefix == '?':
            # ? or ?123
            if not self.at_end() and self.peek().isdigit():
                while not self.at_end() and self.peek().isdigit():
                    self.advance()
        else:
            # :name, @name, $name
            while not self.at_end():
                char = self.peek()
                if char.isalnum() or char == '_':
                    self.advance()
                else:
                    break

        self.emit(TokenType.PARAMETER)

    def lex_operator(self):
        """Lex operators and punctuation"""
        char = self.peek()

        # Two-character operators
        two_char = self.peek_string(2)

        if two_char == '||':
            self.advance()
            self.advance()
            self.emit(TokenType.CONCAT)
        elif two_char == '==':
            self.advance()
            self.advance()
            self.emit(TokenType.EQUAL2)
        elif two_char == '!=':
            self.advance()
            self.advance()
            self.emit(TokenType.NOT_EQUAL)
        elif two_char == '<>':
            self.advance()
            self.advance()
            self.emit(TokenType.NOT_EQUAL2)
        elif two_char == '<=':
            self.advance()
            self.advance()
            self.emit(TokenType.LESS_EQUAL)
        elif two_char == '>=':
            self.advance()
            self.advance()
            self.emit(TokenType.GREATER_EQUAL)
        elif two_char == '<<':
            self.advance()
            self.advance()
            self.emit(TokenType.LEFT_SHIFT)
        elif two_char == '>>':
            self.advance()
            self.advance()
            self.emit(TokenType.RIGHT_SHIFT)
        elif two_char == '->':
            # Check for ->>
            if self.peek(2) == '>':
                self.advance()
                self.advance()
                self.advance()
                self.emit(TokenType.DOUBLE_ARROW)
            else:
                self.advance()
                self.advance()
                self.emit(TokenType.ARROW)
        # Single-character operators
        elif char == '+':
            self.advance()
            self.emit(TokenType.PLUS)
        elif char == '-':
            self.advance()
            self.emit(TokenType.MINUS)
        elif char == '*':
            self.advance()
            self.emit(TokenType.STAR)
        elif char == '/':
            self.advance()
            self.emit(TokenType.SLASH)
        elif char == '%':
            self.advance()
            self.emit(TokenType.PERCENT)
        elif char == '=':
            self.advance()
            self.emit(TokenType.EQUAL)
        elif char == '<':
            self.advance()
            self.emit(TokenType.LESS)
        elif char == '>':
            self.advance()
            self.emit(TokenType.GREATER)
        elif char == '&':
            self.advance()
            self.emit(TokenType.AMPERSAND)
        elif char == '|':
            self.advance()
            self.emit(TokenType.PIPE)
        elif char == '~':
            self.advance()
            self.emit(TokenType.TILDE)
        # Delimiters
        elif char == '(':
            self.advance()
            self.emit(TokenType.LPAREN)
        elif char == ')':
            self.advance()
            self.emit(TokenType.RPAREN)
        elif char == ',':
            self.advance()
            self.emit(TokenType.COMMA)
        elif char == ';':
            self.advance()
            self.emit(TokenType.SEMICOLON)
        elif char == '.':
            self.advance()
            self.emit(TokenType.DOT)
        else:
            self.error(f"Unexpected character: {char}")
