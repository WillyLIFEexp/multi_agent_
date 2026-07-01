# `app/tools/calculator.py`

Read after: [03-utility-history](03-utility-history.md) · Read before: [05-tools-math_helpers](05-tools-math_helpers.md) · [index](00-index.md)

**Single responsibility:** A safe arithmetic evaluator exposed as a LangChain tool — parse an expression string into an AST and evaluate only a whitelisted set of operators, never `eval`. It's a leaf (stdlib + `langchain_core.tools`), collected into `MATH_TOOLS` (doc 07) and bound to the math agent (doc 09).

This is the first tool, so it's the place to explain the safety model the whole `tools/` package follows: **tools take strings, return strings, and never raise into the agent.**

---

## Block 1 — imports and operator tables (lines 1–20)

```python
import ast, operator
from langchain_core.tools import tool
_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
```

- **WHAT:** Maps AST operator node types to their concrete implementations, for both binary and unary operators.
- **WHY a whitelist dict:** this is the security boundary. The evaluator can *only* perform operations present in these tables; anything else (function calls, attribute access, names) has no entry and is rejected. An explicit allowlist is far safer than a denylist — you fail closed on anything you didn't anticipate.
- **WHY `operator.*` functions:** they're the callable forms of `+ - * /` etc., so the evaluator can dispatch `op(left, right)` generically instead of a giant `if/elif` over operator types.

## Block 2 — `_eval_node()` (lines 23–38)

```python
def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)): return node.value
        raise ValueError(...)
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None: raise ValueError(...)
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp): ...
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")
```

- **WHAT:** Recursively evaluates only three node kinds — numeric constants, binary ops, unary ops — raising on anything else.
- **WHY recurse over the AST instead of `eval(expression)`:** `eval` on user/LLM input is a remote-code-execution hole (`__import__("os").system(...)`). Walking the AST and honoring only numeric literals and whitelisted operators means a string like `os.system('rm -rf /')` parses to nodes with no handler and raises — it can never execute. This is the entire reason the file exists rather than a one-line `eval`.
- **WHY reject non-numeric constants explicitly:** `ast.Constant` also covers strings, `None`, etc. The inner `isinstance(..., (int, float))` check ensures `"2" + "3"` style string constants can't slip through as valid.
- **WHY `.get(type(node.op))` then `None`-check:** an operator node whose type isn't in the table (e.g. bitwise `<<`) returns `None` and raises a clear "Unsupported operator" — fail-closed again.

## Block 3 — `safe_eval()` (lines 41–44)

```python
def safe_eval(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)
```

- **WHAT:** Parses in `mode="eval"` (a single expression, not statements) and evaluates the root.
- **WHY `mode="eval"`:** it structurally forbids statements — assignments, imports, `exec` — at the *parse* level. You can't even represent `import os` in an eval-mode tree. A second layer of fail-closed on top of the operator whitelist.
- **WHY a separate non-tool function:** `safe_eval` is the pure, testable core; the `@tool` wrapper below adds the agent-facing error handling. Splitting them means the evaluation logic can be unit-tested without the tool machinery.

## Block 4 — the `@tool calculator` (lines 47–57)

```python
@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression. Supports + - * / // % ** and parentheses..."""
    try:
        return str(safe_eval(expression))
    except Exception as exc:
        return f"Error: {exc}"
```

- **WHAT:** The LangChain tool: takes an expression string, returns the result (or an error string).
- **WHY `@tool` + the docstring:** `@tool` turns the function into a `BaseTool` whose *docstring becomes the description the LLM sees*. "Evaluate a basic arithmetic expression… e.g. `2 * (3 + 4) ** 2`" is how the model learns when and how to call it — the docstring is functional, not decorative.
- **WHY catch `Exception` and return `f"Error: {exc}"` instead of raising:** a tool that raises would abort the agent's tool-execution step. Returning the error *as the tool's string output* feeds it back into the model, which can then correct itself (fix the expression, try another tool). This "never raise into the agent; report errors as text" pattern is shared by every tool in the package. The `# noqa: BLE001` acknowledges the deliberate broad catch.
- **WHY return `str(...)`:** tool outputs must be strings for the LLM; the numeric result is stringified.

---

## Why this shape (tie-back)

The math agent (doc 09) is a `reason → act → respond` loop where `act` runs whatever tool
the model requested. That design only works if tools are (a) safe against adversarial
strings the LLM might synthesize and (b) non-fatal on bad input. This file establishes
both: AST-whitelist safety and error-as-output. The remaining tool files (docs 05–06)
reuse the same string-in/string-out, catch-and-report contract.

Next: [05-tools-math_helpers](05-tools-math_helpers.md) — the number-theory and statistics tools, same contract, simpler bodies. →
