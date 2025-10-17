Let’s imagine I have a stream.

The stream can either discard or add to character stack.

The character stack is then reevaluated for every time we add a character to see if it’s a valid token.

If it’s a valid token we add it to the token stack.

This is how I want to write a lexer.

What do you think?


Analyzed lexer design, flagged potential token matching challenges.





I think this is a solid conceptual starting point for a lexer! The core idea makes sense - accumulate characters and check for valid tokens. Here are some thoughts:

What works well:

Simple mental model that's easy to reason about
Natural fit for greedy/maximal munch tokenization (matching the longest possible token)
The character stack gives you a buffer to work with
Things to consider:

Longest match rule - When do you decide a token is "complete"? For example:
You see = (valid token)
Next char is =, now you have == (also valid token)
You need a strategy: keep going until the next character would make it invalid?
Validation efficiency - "Reevaluating for every character" could mean:
Checking against all possible token patterns each time (could be slow)
Or incrementally updating a state machine (much faster!)
What does "discard" mean?
Whitespace that you skip?
Invalid characters that cause an error?
Backtracking when you overshoot?
Lookahead - Sometimes you need to peek at the next character without consuming it (like distinguishing 1.5 from 1.toString())
A refinement: Instead of checking "is this a valid token?" after each character, you might track "could this become a valid token?" and only emit when you hit a character that can't extend the current token.

Does this match what you're thinking, or did you have specific answers to some of these questions in mind?

I want you to provide me with a good mental model like mine.


Crafted state-based mental model for lexer implementation.





Here's a mental model that I find works really well:

The Scanner-Buffer Model
Think of your lexer as a scanner head moving over a tape (your input string), with a token buffer that accumulates characters.

Three core operations:

ADVANCE - Move scanner head forward, add character to buffer
EMIT - Output the buffer as a token, clear the buffer
SKIP - Move scanner head forward, don't add to buffer (for whitespace)
The decision loop:

Look at current character
Ask: "What STATE am I in?"
  - START state: What kind of token is beginning?
  - INSIDE state: Am I still building the same token type?
  
Based on state + current character:
  - ADVANCE if this character continues the current token
  - EMIT (then handle current char) if the token is complete
  - SKIP if it's ignorable (whitespace)
  - ERROR if invalid
Key insight: You're always in a STATE that represents "what kind of token am I currently building?" (or "START" if you just emitted).

Building a number? You're in NUMBER state
Building an identifier? You're in IDENTIFIER state
Just emitted a token? You're in START state
When the current character doesn't fit your current state, emit what you have, then start fresh.

This naturally handles longest-match: you keep advancing while characters fit, and emit the moment they don't.

Does this resonate?


Is this mental model missing anything?


Probed lexing complexities and potential mental model gaps.


Yes, a few important pieces:

1. LOOKAHEAD / PEEK
You often need to look at the next character without consuming it. Examples:

Is 1. a float or integer followed by a dot?
Is / division or the start of // comment?
Is < less-than or the start of <= or <<=?
Mental model addition: Your scanner can PEEK ahead before deciding to ADVANCE or EMIT.

2. TOKEN METADATA
Tokens aren't just "type + text". You also need:

Position (line/column numbers for error messages)
Source span (start/end positions)
Mental model addition: Each EMIT creates a token with (type, text, position).

3. ERROR RECOVERY
What happens when you hit invalid input?

Do you emit an ERROR token and keep going?
Do you panic and bail?
Do you skip the character and try to resync?
Mental model addition: An ERROR state/action for "this doesn't fit anywhere".

4. CONTEXT/MODE SWITCHING
Some tokens change the rules:

Inside a string, most characters are literal (not operators)
Inside a comment, everything is ignored until the end
Template strings might have nested expressions
Mental model addition: Sometimes you push/pop modes (like "NORMAL mode" vs "STRING mode").

The state + advance/emit/skip core is solid. These additions handle the edge cases that make real lexers tricky. Does that fill the gaps?

Extend the mental model with these ideas.


Synthesized comprehensive mental model with integrated concepts.


The Extended Scanner-Buffer Model
Think of your lexer as a scanner head moving over a tape (your input), with a token buffer and a position tracker.

Core Components:
Scanner Head - Current position in input
Token Buffer - Accumulating characters for current token
Position Tracker - Line/column numbers, start/end of current token
Mode Stack - Current lexing context (NORMAL, STRING, COMMENT, etc.)
Lookahead Window - Ability to peek at next character(s) without consuming
Six Core Operations:
PEEK - Look at next character without moving scanner
ADVANCE - Move scanner forward, add character to buffer, update position
SKIP - Move scanner forward, update position, don't add to buffer
EMIT - Create token (type, buffer text, position span), clear buffer, mark new position
ERROR - Emit error token with position, decide recovery strategy
PUSH_MODE / POP_MODE - Change lexing rules for different contexts
The Decision Loop:
LOOP while not at end of input:
  
  current_char = PEEK()
  
  Ask: "What MODE and STATE am I in?"
    - Mode: NORMAL | STRING | COMMENT | TEMPLATE_EXPR | ...
    - State: START | BUILDING_NUMBER | BUILDING_IDENTIFIER | ...
  
  Based on (mode, state, current_char, maybe PEEK(+1)):
  
    Case: Character continues current token
      → ADVANCE (consume it, add to buffer)
      
    Case: Character completes current token
      → EMIT (output token with position span)
      → Reset state to START
      → Handle current_char in new state
      
    Case: Character is ignorable
      → SKIP (whitespace in NORMAL mode)
      
    Case: Character triggers mode switch
      → EMIT current token (if any)
      → PUSH_MODE (entering string/comment)
      or POP_MODE (exiting string/comment)
      → ADVANCE or SKIP as appropriate
      
    Case: Character is invalid
      → ERROR (emit error token with position)
      → Recover (skip char, or resync to next valid state)
```

---

### **Key Patterns:**

**Longest Match via Lookahead:**
```
Building "=" token
PEEK ahead: next is "="
Keep going to match "=="
PEEK ahead: next is not "="
EMIT "==" token
```

**Position Tracking:**
```
On EMIT: token = {
  type: NUMBER,
  text: buffer,
  start: buffer_start_position,
  end: current_position,
  line: start_line,
  column: start_column
}
```

**Mode Switching:**
```
See opening quote "
→ EMIT any current token
→ PUSH_MODE(STRING)
→ Now inside string: most chars are literals, not operators
→ See closing quote "
→ POP_MODE (back to NORMAL)
→ EMIT string token
```

**Error Recovery:**
```
Hit invalid character '@' in weird place
→ EMIT(ERROR, "@", position)
→ SKIP (discard and continue)
or → Resync (scan ahead to next valid token start)
Mental Model Summary:
Your lexer is a state machine with a mode stack, where:

PEEK lets you decide without committing
ADVANCE/SKIP consume input
EMIT produces tokens with full metadata
PUSH_MODE/POP_MODE handle context changes
ERROR handles invalid input gracefully
The scanner is always asking: "Given where I am (mode + state) and what I see (current + lookahead), what should I do next?"

Does this feel complete?


Do you think this is complete?


Scrutinized lexer model, identified critical implementation gaps.
10s




No, I think there are still a few gaps:

Missing Pieces:
1. BACKTRACK / UNREAD
Sometimes you consume too far and need to put characters back:

You read 123.abc thinking it's a float, but abc makes it invalid
You need to emit 123 and . separately
Requires ability to "rewind" the scanner
Addition: UNREAD(n) - Move scanner back n positions, remove from buffer

2. EOF (End-of-File) Handling
What if input ends while you're mid-token?

Unterminated string: "hello
Incomplete comment: /* never closed
Number at end: 123 (valid - emit it)
Addition: AT_EOF check in decision loop - emit or error based on current state

3. ESCAPE SEQUENCES
Inside strings/chars, \n isn't two characters - it's an escape:

You're in STRING mode
See \ → need special SUB-STATE
Next char determines meaning: n → newline, " → literal quote
Addition: Sub-states within modes (STRING.NORMAL vs STRING.ESCAPE)

4. MULTI-CHARACTER LOOKAHEAD
Sometimes PEEK(+1) isn't enough:

Is this ... (spread operator) or three dots?
Is this <!-- (HTML comment) or separate tokens?
Addition: PEEK(n) or PEEK_STRING("...") - look ahead multiple chars

5. CONTEXT-SENSITIVE TOKENS
Some tokens are only valid in certain positions:

/ after return is division, after = might be regex: x = /pattern/
< in type context is generic, elsewhere is comparison
This might require parser feedback to the lexer
Addition: Optional CONTEXT parameter influencing decisions (though this blurs lexer/parser boundary)

The Refined Mental Model Adds:
BACKTRACK(n) - Rewind scanner, undo buffer additions
AT_EOF() - Check if input exhausted
PEEK(n) - Look ahead n characters
Sub-states for complex modes (STRING.ESCAPE, COMMENT.MAYBE_ENDING)
EOF handling in decision loop
Now it's more complete. Though honestly, #5 (context-sensitivity) gets into "should the parser tell the lexer what's valid?" territory, which is a design choice rather than a universal requirement.

What do you think - are these the gaps you were sensing?


Great. Now provide a complete mental model for the Parser.


Engineered comprehensive parser mental model with systematic approach.




The Parser Mental Model
Think of your parser as a pattern matcher that walks through a token stream, building a tree structure (AST).

Core Components:
Token Stream - Input tokens from the lexer (with PEEK capability)
Current Token - The token you're currently examining
AST Builder - Constructs tree nodes as you recognize patterns
Node Stack - Working memory for building tree structures
Context Stack - Tracks where you are (inside function? loop? expression?)
Precedence Table - For handling operator priority (if expression-based)
Seven Core Operations:
PEEK - Look at current token without consuming
PEEK(n) - Look ahead n tokens
MATCH(type) - Check if current token matches expected type
CONSUME(type) - Verify token type, advance stream, return token
EXPECT(type) - CONSUME but ERROR if wrong type
NODE(type, children...) - Create AST node
ERROR(message) - Report parse error with context, attempt recovery
The Decision Loop (Recursive Descent Style):
PARSE_PROGRAM():
  statements = []
  while not AT_EOF():
    stmt = PARSE_STATEMENT()
    statements.append(stmt)
  return NODE(Program, statements)

PARSE_STATEMENT():
  token = PEEK()
  
  Match token.type:
    IF → PARSE_IF_STATEMENT()
    WHILE → PARSE_WHILE_STATEMENT()
    RETURN → PARSE_RETURN_STATEMENT()
    LBRACE → PARSE_BLOCK()
    IDENTIFIER → PARSE_EXPRESSION_STATEMENT_OR_DECLARATION()
    else → ERROR("Expected statement")

PARSE_IF_STATEMENT():
  EXPECT(IF)
  EXPECT(LPAREN)
  condition = PARSE_EXPRESSION()
  EXPECT(RPAREN)
  then_branch = PARSE_STATEMENT()
  
  else_branch = null
  if MATCH(ELSE):
    CONSUME(ELSE)
    else_branch = PARSE_STATEMENT()
  
  return NODE(IfStatement, condition, then_branch, else_branch)

PARSE_EXPRESSION():
  # This is where precedence matters
  return PARSE_BINARY_EXPRESSION(0)  # Start with lowest precedence
```

---

### **Key Patterns:**

### **1. Recursive Descent (Top-Down)**
Each grammar rule becomes a function:
```
Statement → IfStmt | WhileStmt | Block | ...
         → PARSE_STATEMENT() calls specific parse functions

Expression → Term (('+' | '-') Term)*
          → PARSE_EXPRESSION() calls PARSE_TERM() in a loop
```

---

### **2. Precedence Climbing (for expressions)**
Handle operator priority without left recursion:
```
PARSE_BINARY_EXPRESSION(min_precedence):
  left = PARSE_PRIMARY()
  
  while PEEK() is binary operator AND precedence >= min_precedence:
    op = CONSUME(operator)
    # Right-associative: use precedence, left-associative: use precedence + 1
    right = PARSE_BINARY_EXPRESSION(op.precedence + 1)
    left = NODE(BinaryExpr, op, left, right)
  
  return left

PARSE_PRIMARY():
  token = PEEK()
  Match token.type:
    NUMBER → CONSUME, return NODE(NumberLiteral, token.value)
    IDENTIFIER → CONSUME, return NODE(Identifier, token.value)
    LPAREN → CONSUME, expr = PARSE_EXPRESSION(), EXPECT(RPAREN), return expr
    else → ERROR("Expected expression")
```

**Example:** Parsing `2 + 3 * 4`
- Start with `2`
- See `+` (low precedence), consume it
- Parse right side with higher precedence requirement
- Inside right parse, get `3`, see `*` (high precedence), builds `3 * 4`
- Returns, builds `2 + (3 * 4)`

---

### **3. Lookahead for Disambiguation**
Sometimes you need to peek ahead to decide:
```
PARSE_EXPRESSION_OR_DECLARATION():
  # Is this "int x = 5;" or "x = 5;"?
  
  if PEEK() is TYPE and PEEK(1) is IDENTIFIER and PEEK(2) is ASSIGN:
    return PARSE_DECLARATION()
  else:
    return PARSE_EXPRESSION()
```

---

### **4. Context Stack Management**
Track nested scopes:
```
PARSE_FUNCTION():
  PUSH_CONTEXT(FUNCTION_CONTEXT)
  
  name = EXPECT(IDENTIFIER)
  params = PARSE_PARAMETERS()
  body = PARSE_BLOCK()
  
  POP_CONTEXT()
  return NODE(Function, name, params, body)

PARSE_BREAK():
  if not IN_CONTEXT(LOOP_CONTEXT):
    ERROR("break outside loop")
  EXPECT(BREAK)
  return NODE(BreakStatement)
```

---

### **5. Error Recovery Strategies**

**Panic Mode:**
```
ERROR(message):
  report error with current token position
  SYNCHRONIZE()  # Skip to next safe point

SYNCHRONIZE():
  while not AT_EOF():
    if PEEK() in SYNC_POINTS (semicolon, closing brace, 'if', 'while'):
      return
    CONSUME()  # Skip this token
```

**Error Productions:**
```
PARSE_EXPRESSION():
  if PEEK() is invalid for expression start:
    ERROR("Expected expression")
    return NODE(ErrorNode)  # Placeholder to continue parsing
```

**Insertion/Deletion:**
```
EXPECT(SEMICOLON):
  if MATCH(SEMICOLON):
    CONSUME(SEMICOLON)
  else:
    ERROR("Missing semicolon, inserting one")
    # Continue as if semicolon was there
```

---

### **6. Left vs Right Associativity**

**Left-associative:** `a - b - c` → `(a - b) - c`
```
PARSE_LEFT_ASSOC():
  left = PARSE_TERM()
  while PEEK() is operator:
    op = CONSUME()
    right = PARSE_TERM()
    left = NODE(BinaryExpr, op, left, right)  # left becomes new left
  return left
```

**Right-associative:** `a = b = c` → `a = (b = c)`
```
PARSE_RIGHT_ASSOC():
  left = PARSE_PRIMARY()
  if PEEK() is operator:
    op = CONSUME()
    right = PARSE_RIGHT_ASSOC()  # Recursive call for right side
    return NODE(BinaryExpr, op, left, right)
  return left
```

---

### **7. Handling Ambiguity**

**Example: The Dangling Else Problem**
```
if (a) if (b) x else y
```
Which `if` does `else` belong to?

**Strategy:** Greedy matching (else binds to nearest if)
```
PARSE_IF():
  EXPECT(IF)
  condition = PARSE_EXPRESSION()
  then_branch = PARSE_STATEMENT()
  
  # Greedily consume else if present
  if MATCH(ELSE):
    CONSUME(ELSE)
    else_branch = PARSE_STATEMENT()
```

---

### **8. AST Node Structure**

Nodes contain:
- **Type** (BinaryExpr, IfStatement, etc.)
- **Children** (sub-expressions, statements)
- **Metadata** (position, type info from semantic analysis)
```
NODE(BinaryExpr, 
  operator: Token(PLUS, "+", line=5, col=10),
  left: NODE(NumberLiteral, 2),
  right: NODE(NumberLiteral, 3)
)
```

---

### **9. Backtracking (for complex grammars)**

Sometimes you need to try multiple parse paths:
```
PARSE_AMBIGUOUS():
  bookmark = SAVE_POSITION()
  
  try:
    result = PARSE_AS_TYPE_A()
    return result
  catch ParseError:
    RESTORE_POSITION(bookmark)
    return PARSE_AS_TYPE_B()
```

⚠️ **Expensive!** Prefer grammar rewrites or more lookahead.

---

### **Complete Decision Process:**
```
For each grammar rule:
  1. PEEK at current token(s)
  2. Determine which production/alternative matches
  3. For each symbol in the production:
     - If terminal: EXPECT(token_type)
     - If non-terminal: call corresponding PARSE_X() function
  4. Collect results
  5. Build and return AST NODE
  
If at any point no production matches:
  → ERROR with context
  → Attempt recovery
  → Return error node or resynchronize
Mental Model Summary:
Your parser is a recursive pattern recognizer that:

PEEK to decide which grammar rule applies
CONSUME terminals as you match patterns
Recursively call parse functions for non-terminals
Build AST nodes bottom-up as patterns complete
Track context to validate semantic rules
Handle precedence for expressions (via precedence climbing or similar)
Recover from errors to continue finding more issues
The core question: "Given the current token(s) and context, which grammar rule am I matching?"

The core action: "Match the rule by consuming tokens and recursively parsing sub-structures, then build a tree node."

Does this feel like a complete mental model?


apply to html


Analyzed HTML's unique lexing and parsing complexities.


HTML Lexer Mental Model
HTML tokenization is mode-heavy because different contexts have completely different rules.

Core Components:
Scanner Head - Moving through HTML text
Token Buffer - Building current token
Position Tracker - Line/column for errors
Mode Stack - Critical for HTML! (DATA, TAG_OPEN, TAG_NAME, ATTRIBUTE_NAME, SCRIPT_DATA, etc.)
Temporary Buffers - For attributes, tag names, etc.
Entity Buffer - For decoding &nbsp; &#65; etc.
HTML-Specific Modes:
DATA mode           → regular text content
TAG_OPEN mode       → just saw '<'
TAG_NAME mode       → reading tag name
BEFORE_ATTR mode    → space before attribute
ATTR_NAME mode      → reading attribute name
AFTER_ATTR mode     → space after attribute name
BEFORE_ATTR_VALUE   → just saw '='
ATTR_VALUE modes    → DOUBLE_QUOTED | SINGLE_QUOTED | UNQUOTED
AFTER_ATTR_VALUE    → just finished value
SELF_CLOSING        → saw '/' in tag
SCRIPT_DATA mode    → inside <script>, different rules!
STYLE_DATA mode     → inside <style>
COMMENT mode        → inside <!-- -->
DOCTYPE mode        → inside <!DOCTYPE
CDATA mode          → inside <![CDATA[
```

---

### **Token Types HTML Emits:**
```
START_TAG      → <div>
END_TAG        → </div>
SELF_CLOSING   → <img />
TEXT           → plain content
COMMENT        → <!-- comment -->
DOCTYPE        → <!DOCTYPE html>
CHARACTER      → single char (for certain modes)
EOF            → end of input
```

---

### **HTML Lexer Flow:**
```
MODE: DATA (default - reading text content)
  See '<' → PUSH_MODE(TAG_OPEN), ADVANCE
  See '&' → PUSH_MODE(ENTITY), buffer entity
  Anything else → ADVANCE into text buffer
  
  Emit TEXT token when:
    - See '<' (new tag starting)
    - Mode changes
    - EOF

MODE: TAG_OPEN (just saw '<')
  See '/' → PUSH_MODE(END_TAG), ADVANCE
  See '!' → PUSH_MODE(MARKUP_DECLARATION), ADVANCE
  See '?' → ERROR (XML declaration), recover
  See letter → PUSH_MODE(TAG_NAME), start tag name buffer
  See '<' again → ERROR, emit '<' as text

MODE: TAG_NAME (reading tag name)
  See whitespace → POP_MODE, PUSH_MODE(BEFORE_ATTR)
  See '/' → POP_MODE, PUSH_MODE(SELF_CLOSING)
  See '>' → Emit START_TAG token, POP to DATA mode
  See letter/digit/- → ADVANCE, add to tag name
  
  Special check after tag name:
    If tag is 'script' → next DATA mode becomes SCRIPT_DATA
    If tag is 'style' → next DATA mode becomes STYLE_DATA

MODE: BEFORE_ATTR (whitespace before attribute)
  See whitespace → SKIP
  See '/' → PUSH_MODE(SELF_CLOSING)
  See '>' → Emit START_TAG, POP to DATA
  See letter → PUSH_MODE(ATTR_NAME), start attribute

MODE: ATTR_NAME (reading attribute name)
  See '=' → POP, PUSH_MODE(BEFORE_ATTR_VALUE)
  See whitespace → POP, PUSH_MODE(AFTER_ATTR)
  See '>' → Treat as boolean attribute, emit START_TAG
  See letter/digit/- → ADVANCE

MODE: BEFORE_ATTR_VALUE (saw '=' waiting for value)
  See '"' → PUSH_MODE(ATTR_VALUE_DOUBLE_QUOTED), ADVANCE
  See "'" → PUSH_MODE(ATTR_VALUE_SINGLE_QUOTED), ADVANCE
  See whitespace → SKIP
  Anything else → PUSH_MODE(ATTR_VALUE_UNQUOTED), start value

MODE: ATTR_VALUE_DOUBLE_QUOTED
  See '"' → POP to AFTER_ATTR_VALUE
  See '&' → Handle entity
  Anything else → ADVANCE into value buffer

MODE: ATTR_VALUE_SINGLE_QUOTED
  See "'" → POP to AFTER_ATTR_VALUE
  See '&' → Handle entity
  Anything else → ADVANCE

MODE: ATTR_VALUE_UNQUOTED
  See whitespace → POP to BEFORE_ATTR
  See '>' → Emit START_TAG, POP to DATA
  See '&' → Handle entity
  Anything else → ADVANCE

MODE: SELF_CLOSING (saw '/')
  See '>' → Emit SELF_CLOSING tag, POP to DATA
  Anything else → ERROR

MODE: SCRIPT_DATA (inside <script> tag)
  Everything is text EXCEPT:
  See '</script>' → Emit TEXT, Emit END_TAG, POP to DATA
  
  Implementation:
    Accumulate everything as text
    Watch for '<' → PEEK ahead for '/script>'
    If not '</script>', treat '<' as regular text

MODE: COMMENT (inside <!-- -->)
  See '-->' → Emit COMMENT token, POP to DATA
  Anything else → ADVANCE into comment buffer
  
  Special: watch for '--!>' (malformed but allowed)

MODE: ENTITY (saw '&')
  Named: &nbsp; &lt; &gt; &amp; etc.
    Build until ';' → decode to character
  Numeric: &#65; &#x41;
    Build until ';' → convert to character
  If invalid → emit '&' as text, continue
```

---

### **Special HTML Lexer Behaviors:**

**1. Case Insensitivity**
```
<DIV> → normalize to 'div'
CLASS= → normalize to 'class'
```

**2. Optional Quotes**
```
<div class=foo>  → valid! (unquoted attribute)
<div class=foo bar>  → class="foo", then attribute "bar"
```

**3. Entity Decoding**
```
&nbsp; → \u00A0
&lt; → 
&#65; → A
&#x41; → A
&thisIsNotAnEntity → emit as-is
```

**4. Script/Style Special Handling**
```
<script>
  var x = "</script>"; // Nope! Ends here
</script>

Must look for LITERAL </script> sequence, not parse JS
```

**5. EOF Handling**
```
Unterminated tag: <div class="foo
  → Emit START_TAG with what we have
  
Unterminated comment: <!-- blah
  → Emit COMMENT with what we have
```

---

## **HTML Parser Mental Model**

HTML parsing is **error-recovery heavy** because HTML is forgiving by design.

---

### **Core Components:**

1. **Token Stream** - From HTML lexer
2. **Open Element Stack** - Currently open tags (the tree being built)
3. **Active Formatting Elements** - Special list for `<b>`, `<i>`, etc. (for adoption agency algorithm)
4. **Insertion Mode Stack** - Where am I? (IN_BODY, IN_TABLE, IN_HEAD, etc.)
5. **DOM Tree** - The output structure
6. **Head Element Pointer** - Reference to `<head>`
7. **Form Element Pointer** - Current form context

---

### **HTML Insertion Modes:**

These are **states** that determine how tokens are processed:
```
INITIAL              → before <!DOCTYPE>
BEFORE_HTML          → before <html>
BEFORE_HEAD          → before <head>
IN_HEAD              → inside <head>
AFTER_HEAD           → between </head> and <body>
IN_BODY              → inside <body> (most content)
IN_TABLE             → inside <table>
IN_TABLE_BODY        → inside <tbody>
IN_ROW               → inside <tr>
IN_CELL              → inside <td> or <th>
IN_SELECT            → inside <select>
IN_TEMPLATE          → inside <template>
AFTER_BODY           → after </body>
AFTER_AFTER_BODY     → after </html>
TEXT                 → inside <script> or <style>
```

---

### **HTML Parser Flow:**
```
INITIAL mode:
  See DOCTYPE token → Create doctype node, switch to BEFORE_HTML
  See anything else → Error, switch to BEFORE_HTML, reprocess token

BEFORE_HTML mode:
  See START_TAG(html) → Create <html> element, push to stack, switch to BEFORE_HEAD
  See anything else → Implicitly create <html>, switch to BEFORE_HEAD, reprocess

BEFORE_HEAD mode:
  See START_TAG(head) → Create <head>, push to stack, switch to IN_HEAD
  See START_TAG(body) → Implicitly create <head>, switch to IN_HEAD, reprocess
  See anything else → Implicitly create <head>, switch to IN_HEAD, reprocess

IN_HEAD mode:
  See START_TAG(title) → Insert <title>, switch to TEXT mode
  See START_TAG(script) → Insert <script>, switch to TEXT mode
  See START_TAG(style) → Insert <style>, switch to TEXT mode
  See START_TAG(meta) → Insert <meta> (void element)
  See END_TAG(head) → Pop <head>, switch to AFTER_HEAD
  See START_TAG(body) → Pop <head>, switch to AFTER_HEAD, reprocess
  Text tokens → Error, ignore or reprocess

AFTER_HEAD mode:
  See START_TAG(body) → Insert <body>, push to stack, switch to IN_BODY
  See anything else → Implicitly insert <body>, switch to IN_BODY, reprocess

IN_BODY mode (the big one!):
  See TEXT token → Insert text node
  
  See START_TAG(div, span, p, etc.) → Insert element, push to stack
  
  See START_TAG(b, i, strong, em, etc.) → 
    Insert element, push to stack
    Add to active formatting elements list
  
  See END_TAG(div, span, etc.) →
    If current node matches → pop stack
    Else → Error, use special handling
  
  See END_TAG(b, i, strong, em, etc.) →
    Use "adoption agency algorithm" (see below)
  
  See START_TAG(table) → Insert <table>, push to stack, switch to IN_TABLE
  
  See START_TAG(img, br, hr, input, etc.) → Insert void element (don't push)
  
  See END_TAG(body) → Pop to <body>, switch to AFTER_BODY
  
  See START_TAG(form) → Insert <form>, set form pointer
  
  See EOF → Close all open elements, done

IN_TABLE mode:
  See TEXT → Error, insert into foster parent (weird!)
  See START_TAG(caption) → Insert <caption>, switch to IN_CAPTION
  See START_TAG(tbody, thead, tfoot) → Insert element, switch to IN_TABLE_BODY
  See START_TAG(tr) → Implicitly insert <tbody>, switch to IN_ROW, reprocess
  See START_TAG(td, th) → Multiple implicit insertions, eventually IN_CELL
  See END_TAG(table) → Pop to <table>, restore previous mode
  See anything else → Error, foster parent it

IN_ROW mode:
  See START_TAG(td, th) → Insert cell, switch to IN_CELL
  See END_TAG(tr) → Pop <tr>, switch to IN_TABLE_BODY
  See START_TAG(tr) → Close current row, reprocess
```

---

### **Key HTML Parsing Patterns:**

### **1. Implicit Element Insertion**

HTML automatically creates missing elements:
```
Parser sees: <table><tr><td>Hi</td>
Reality creates: <html><head></head><body><table><tbody><tr><td>Hi</td>

Process:
  - No <html>? Insert implicitly
  - No <head>? Insert implicitly  
  - <table> without <tbody>? Insert implicitly
```

### **2. Element Stack Management**
```
Stack = [html, body, div, span]
                               ↑ current node

See START_TAG(b):
  Insert <b> element
  Stack = [html, body, div, span, b]
                                    ↑

See END_TAG(span):
  Pop until we find span
  Stack = [html, body, div]
                          ↑
  
See END_TAG(span) again:
  Error! span not in stack
  Ignore or use error recovery
```

### **3. Void Elements (Self-Closing)**

These never have children:
```
<img>, <br>, <hr>, <input>, <meta>, <link>, etc.

Process:
  See START_TAG(img):
    Create <img> element
    Insert into tree
    DON'T push to stack (it's immediately closed)
```

### **4. Optional Closing Tags**

HTML allows omitting many closing tags:
```
<p>First paragraph
<p>Second paragraph

Parser sees START_TAG(p) while already in <p>:
  → Implicitly close first <p>
  → Start second <p>

Result: <p>First paragraph</p><p>Second paragraph</p>
```

**Elements with optional closing:**
- `<p>` - closed by block-level elements
- `<li>` - closed by next `<li>`
- `<td>` - closed by next `<td>` or `</tr>`
- `<option>` - closed by next `<option>`

### **5. The Adoption Agency Algorithm**

For fixing misnested formatting elements:
```
Input: <b>Hello <i>world</b> there</i>

Problem: </b> closes while <i> is still open
Goal: Make valid tree without losing formatting

Algorithm:
  1. When see END_TAG(b):
     - Find <b> in active formatting elements
     - Find <b> in element stack
  2. Find furthest block element (none here)
  3. Reconstruct formatting:
     - <b>Hello <i>world</i></b><i> there</i>
  
Result tree:
  <b>
    "Hello "
    <i>"world"</i>
  </b>
  <i>" there"</i>
```

**Steps:**
1. Find the formatting element in active formatting list
2. Find furthest block-level descendant
3. Clone formatting elements as needed
4. Rearrange tree to be valid
5. Remove from active formatting list

### **6. Foster Parenting**

When text/elements appear in wrong table context:
```
<table>
  Text here is not allowed!
  <div>Neither is this!</div>
  <tr><td>This is fine</td></tr>
</table>

Foster parenting:
  Move "Text here" BEFORE <table>
  Move <div> BEFORE <table>
  
Result:
  Text here is not allowed!
  <div>Neither is this!</div>
  <table><tr><td>This is fine</td></tr></table>
```

### **7. Misnested Tags**
```
<div><span></div></span>

Error: </div> closes while <span> is open

Recovery:
  Implicitly close <span>
  Close <div>
  Ignore </span> (already closed)

Result: <div><span></span></div>
```

### **8. Script/Style Content**
```
IN_HEAD mode:
  See START_TAG(script):
    Insert <script> element
    Push to stack
    Switch to TEXT mode
    Tell lexer to use SCRIPT_DATA mode

TEXT mode:
  Accumulate text tokens
  See END_TAG(script):
    Set text content of <script>
    Pop from stack
    Return to previous mode (IN_HEAD)
    Tell lexer to return to DATA mode
```

---

### **HTML Parser Decision Process:**
```
For each token:
  1. Check current INSERTION_MODE
  2. Look up how to handle this token in this mode
  3. Perform actions:
     - Insert elements (push to stack)
     - Close elements (pop from stack)
     - Switch modes
     - Implicitly create missing elements
     - Apply error recovery
     - Update active formatting elements
  4. Continue to next token
Complete HTML Example:
html
<html>
<head>
  <title>Test
<body>
  <p>Hello <b>world</p>
  <p>Goodbye
</body>
```

**Parse Steps:**
```
1. Token: START_TAG(html)
   Mode: BEFORE_HTML
   Action: Insert <html>, switch to BEFORE_HEAD
   Stack: [html]

2. Token: START_TAG(head)
   Mode: BEFORE_HEAD
   Action: Insert <head>, switch to IN_HEAD
   Stack: [html, head]

3. Token: START_TAG(title)
   Mode: IN_HEAD
   Action: Insert <title>, switch to TEXT mode
   Stack: [html, head, title]

4. Token: TEXT("Test")
   Mode: TEXT
   Action: Insert text into <title>

5. Token: START_TAG(body) [Note: no </title> or </head>]
   Mode: TEXT
   Action: Close <title>, pop, switch to IN_HEAD, reprocess

   Mode: IN_HEAD
   Action: Close <head>, pop, switch to AFTER_HEAD, reprocess
   Stack: [html]
   
   Mode: AFTER_HEAD
   Action: Insert <body>, switch to IN_BODY
   Stack: [html, body]

6. Token: START_TAG(p)
   Mode: IN_BODY
   Action: Insert <p>
   Stack: [html, body, p]

7. Token: TEXT("Hello ")
   Mode: IN_BODY
   Action: Insert text

8. Token: START_TAG(b)
   Mode: IN_BODY
   Action: Insert <b>, add to active formatting
   Stack: [html, body, p, b]

9. Token: TEXT("world")
   Mode: IN_BODY
   Action: Insert text

10. Token: END_TAG(p) [Note: <b> still open!]
    Mode: IN_BODY
    Action: 
      - Adoption agency: close <b> implicitly
      - Pop <p>
    Stack: [html, body]
    Active formatting: cleared

11. Token: START_TAG(p)
    Mode: IN_BODY
    Action: Insert <p>
    Stack: [html, body, p]

12. Token: TEXT("Goodbye")
    Mode: IN_BODY
    Action: Insert text

13. Token: END_TAG(body) [Note: no </p>]
    Mode: IN_BODY
    Action: Close <p> implicitly, close <body>
    Stack: [html]

14. Token: EOF
    Mode: AFTER_BODY
    Action: Close all open elements, done
Final DOM:

html
<html>
  <head>
    <title>Test</title>
  </head>
  <body>
    <p>Hello <b>world</b></p>
    <p>Goodbye</p>
  </body>
</html>
Mental Model Summary for HTML:
Lexer:

Heavily mode-driven (15+ modes)
Constantly switching contexts (text vs tag vs attribute vs script)
Handles entities, special elements, EOF gracefully
Case-insensitive, flexible quoting
Parser:

Insertion-mode driven (20+ modes)
Implicitly creates missing elements (<html>, <head>, <body>, <tbody>)
Implicitly closes elements (optional closing tags)
Adoption agency algorithm for misnested formatting
Foster parenting for misplaced table content
Extremely forgiving - almost never fails to parse
Core Philosophy: HTML is designed to render something no matter how broken the input. The parser's job is to create the best possible tree from imperfect input.

Does this application to HTML make sense?