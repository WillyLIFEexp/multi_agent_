# `app/tools/math_helpers.py`

Read after: [04-tools-calculator](04-tools-calculator.md) · Read before: [06-tools-symbolic](06-tools-symbolic.md) · [index](00-index.md)

**Single responsibility:** A set of discrete-math / statistics tools — `square_root`, `factorial`, `gcd`, `lcm`, `is_prime`, `mean`, `median` — each a thin, safe wrapper over Python's `math`/`statistics` stdlib. Leaves; collected into `MATH_TOOLS` (doc 07) and bound to the math agent (doc 09). They follow the same string-out / error-as-text contract established in doc 04.

---

## Block 1 — imports (lines 1–5)

```python
import math, statistics
from langchain_core.tools import tool
```

- **WHAT:** Stdlib numeric modules + the `@tool` decorator.
- **WHY stdlib instead of reimplementing:** `math.gcd`, `math.factorial`, `statistics.median` are correct, fast, and battle-tested. Reimplementing them would add bugs for no benefit. The tools' value is *exposing* these to the LLM with typed signatures and guardrails, not reinventing the math.

## Block 2 — the guarded tools: `square_root`, `factorial` (lines 8–21)

```python
@tool
def square_root(x: float) -> str:
    """Return the square root of a non-negative number."""
    if x < 0: return "Error: cannot take square root of a negative number"
    return str(math.sqrt(x))

@tool
def factorial(n: int) -> str:
    """Return n! for a non-negative integer n."""
    if n < 0: return "Error: factorial is undefined for negative numbers"
    return str(math.factorial(n))
```

- **WHAT:** Compute √x and n!, but pre-check the domain.
- **WHY the explicit domain guards:** `math.sqrt(-1)` raises `ValueError` and `math.factorial(-1)` raises too — a raise would abort the agent's tool step. Returning `"Error: ..."` instead keeps the failure *inside the conversation* so the model can react (e.g. tell the user the input is invalid). Same "report, don't raise" pattern as the calculator, applied at the domain level.
- **WHY typed params (`x: float`, `n: int`):** `@tool` derives the tool's argument schema from these annotations, so the LLM is told to pass a number, and LangChain coerces/validates the argument before the body runs. `int` vs `float` communicates intent (factorial wants an integer).

## Block 3 — `gcd`, `lcm` (lines 24–33)

```python
@tool
def gcd(a: int, b: int) -> str: return str(math.gcd(a, b))
@tool
def lcm(a: int, b: int) -> str: return str(math.lcm(a, b))
```

- **WHAT:** Two-integer gcd/lcm.
- **WHY no guard here:** `math.gcd`/`math.lcm` are total over integers (including zero/negatives) — there's no domain error to pre-empt, so adding a guard would be noise. The absence of a guard is deliberate, not an oversight: guards appear only where the stdlib would actually raise.

## Block 4 — `is_prime` (lines 36–44)

```python
@tool
def is_prime(n: int) -> str:
    if n < 2: return "False"
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0: return "False"
    return "True"
```

- **WHAT:** Trial-division primality test up to √n.
- **WHY `math.isqrt(n)` as the loop bound:** a factor larger than √n implies a co-factor smaller than √n, so checking up to √n is sufficient and turns an O(n) scan into O(√n). `isqrt` is exact integer sqrt (no float rounding bugs at boundaries).
- **WHY return the strings `"True"`/`"False"`:** tool outputs are strings for the LLM; stringifying the boolean keeps the contract uniform. ⚠ PROD: trial division is fine for the small numbers a tutoring agent sees, but it's slow for very large `n`; a Miller–Rabin test would be the scalable choice.

## Block 5 — `mean`, `median` (lines 47–60)

```python
@tool
def mean(numbers: list[float]) -> str:
    if not numbers: return "Error: empty list"
    return str(statistics.mean(numbers))
# median likewise
```

- **WHAT:** Aggregate statistics over a list.
- **WHY `list[float]` params:** `@tool` maps this to an array-of-number argument schema, so the model knows to pass a list. This is the only tool group taking a collection — the annotation is what makes that legible to the LLM.
- **WHY the empty-list guard:** `statistics.mean([])` raises `StatisticsError`. The guard converts it to the standard error-as-text so an empty input doesn't abort the agent.

---

## Why this shape (tie-back)

These seven tools plus the calculator (doc 04) and the symbolic tools (doc 06) are the
*capabilities* the math agent's `reason` node chooses among (doc 09). Every one follows the
same discipline — typed args so the LLM calls them correctly, string returns, and
domain/empty guards that report errors as text rather than raising — so the agent's tool
loop is robust no matter what arguments the model dreams up. The typed signatures are
doing double duty: runtime validation *and* the schema the model routes on.

Next: [06-tools-symbolic](06-tools-symbolic.md) — the SymPy-backed algebra/calculus tools. →
