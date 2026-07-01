# `app/tools/symbolic.py`

Read after: [05-tools-math_helpers](05-tools-math_helpers.md) · Read before: [07-tools-init](07-tools-init.md) · [index](00-index.md)

**Single responsibility:** Symbolic-math tools backed by SymPy — `solve_equation`, `derivative`, `integrate`, `simplify_expr`. Leaves; collected into `MATH_TOOLS` (doc 07) and bound to the math agent (doc 09). Same string-out / error-as-text contract as the other tools.

These are what make the math agent more than a calculator: exact algebra and calculus, not floating-point approximation.

---

## Block 1 — imports and `_parse` (lines 1–8)

```python
import sympy as sp
from langchain_core.tools import tool

def _parse(expr: str) -> sp.Expr:
    return sp.sympify(expr)
```

- **WHAT:** A shared helper that turns an expression string into a SymPy expression.
- **WHY centralize parsing in `_parse`:** all four tools need string → `sp.Expr`; one helper keeps the conversion (and any future hardening of it) in a single place.
- **⚠ PROD — the real caveat of this file:** `sp.sympify` is **not** a safe evaluator. By default it can evaluate names and certain callables, so passing untrusted input to `sympify` has known code-execution risks. The calculator (doc 04) went to great lengths to avoid exactly this with an AST whitelist; here the code leans on SymPy for expressiveness and accepts the LLM as the (semi-trusted) source of expressions. The comment "no arbitrary code runs" is optimistic. One-line hardening: `sp.parse_expr(expr, evaluate=True)` with a restricted `local_dict`/`transformations`, or validate against a symbol whitelist before parsing. Worth flagging because it's the sharpest security asymmetry in the tool package.

## Block 2 — `solve_equation` (lines 11–28)

```python
@tool
def solve_equation(equation: str, variable: str = "x") -> str:
    try:
        var = sp.Symbol(variable)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            expr = _parse(lhs) - _parse(rhs)
        else:
            expr = _parse(equation)
        return str(sp.solve(expr, var))
    except Exception as exc:
        return f"Error: {exc}"
```

- **WHAT:** Solves `equation` for `variable`, accepting either `"2*x+1 = 5"` (with `=`) or `"x**2 - 4"` (implicitly `= 0`).
- **WHY normalize `lhs = rhs` into `lhs - rhs`:** SymPy's `solve` finds roots of an expression (where it equals zero). Moving everything to one side (`lhs - rhs = 0`) is the standard reduction that lets one code path handle both equation forms.
- **WHY `split("=", 1)` (maxsplit 1):** guards against a stray second `=` producing three parts and an unpack error; only the first `=` splits sides.
- **WHY `variable` defaults to `"x"`:** the overwhelmingly common case; the LLM can override for `t`, `y`, etc. The default keeps simple calls terse.

## Block 3 — `derivative` (lines 31–38)

```python
@tool
def derivative(expression: str, variable: str = "x", order: int = 1) -> str:
    try:
        var = sp.Symbol(variable)
        return str(sp.diff(_parse(expression), var, order))
    except Exception as exc:
        return f"Error: {exc}"
```

- **WHAT:** nth-order derivative of an expression w.r.t. a variable.
- **WHY expose `order`:** a single tool covers first, second, … derivatives without the agent chaining calls. Defaulting to `1` keeps the common case simple while enabling `d²/dx²` in one shot.

## Block 4 — `integrate`, `simplify_expr` (lines 41–57)

```python
@tool
def integrate(expression, variable="x"): return str(sp.integrate(_parse(expression), var))
@tool
def simplify_expr(expression): return str(sp.simplify(_parse(expression)))
```

- **WHAT:** Indefinite integral and algebraic simplification.
- **WHY `integrate` is indefinite (no bounds):** matches the tutoring use case ("integrate x^2") and keeps the signature minimal; definite integration would need limit args. A deliberate scope choice.
- **WHY the same `try/except` wrapper on every tool:** SymPy raises a variety of exceptions on unparseable or unsolvable input; the uniform catch-and-return keeps any failure inside the agent's conversation rather than aborting its tool step — the package-wide contract from doc 04.

---

## Why this shape (tie-back)

`solve/diff/integrate/simplify` are why the math specialist can produce a genuine
`MathResult` with correct symbolic `steps` (doc 09) rather than an LLM's fallible mental
math — the `SYSTEM_PROMPT` there explicitly says "prefer tools." The design tension worth
remembering: these tools trade the calculator's strict AST-safety for SymPy's power, so
they're the part of the tool surface most worth hardening before untrusted exposure.

Next: [07-tools-init](07-tools-init.md) — the registry that gathers all these tools into the `MATH_TOOLS` list the agent binds. →
