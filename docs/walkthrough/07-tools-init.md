# `app/tools/__init__.py`

Read after: [06-tools-symbolic](06-tools-symbolic.md) · Read before: [08-chain-base](08-chain-base.md) · [index](00-index.md)

**Single responsibility:** The tool registry — import every `@tool` from the tool modules (docs 04–06) and expose them as one `MATH_TOOLS` list (plus individual re-exports). It's the single import surface the math agent uses; imported by `chain/math_agent.py` (doc 09) and the router's `ToolNode`.

Small file, but it's the seam between "a pile of tool functions" and "the capability set of the math agent."

---

## Block 1 — the imports (lines 2–12)

```python
from app.tools.calculator import calculator
from app.tools.math_helpers import (factorial, gcd, is_prime, lcm, mean, median, square_root)
from app.tools.symbolic import derivative, integrate, simplify_expr, solve_equation
```

- **WHAT:** Pulls each decorated tool object from its module.
- **WHY re-import here rather than let callers import from each module:** it gives the package a single, stable entry point. `math_agent.py` does `from app.tools import MATH_TOOLS` and is decoupled from *where* each tool physically lives — you can split `symbolic.py` into two files or move `is_prime` without touching any consumer. The `__init__` absorbs that churn.

## Block 2 — `MATH_TOOLS` (lines 14–27)

```python
MATH_TOOLS = [
    calculator, solve_equation, derivative, integrate, simplify_expr,
    square_root, factorial, gcd, lcm, is_prime, mean, median,
]
```

- **WHAT:** The ordered list of all twelve tools bound to the math agent.
- **WHY a single list constant:** the math agent binds tools in exactly two places — `get_llm().bind_tools(MATH_TOOLS)` for the reasoning node and `ToolNode(MATH_TOOLS)` for the execution node (doc 09). Both must see the *same* set or the model could request a tool the executor can't run. One shared constant guarantees they agree. Passing the list twice from a single source is the mechanism that keeps "what the model can call" and "what the graph can execute" in lockstep.
- **WHY a plain list (order + curation):** the order is the order the model sees the tools; grouping the calculator and symbolic tools first is a mild nudge toward the "prefer tools" behavior. It's also a *curated* set — you could imagine history tools existing, but `MATH_TOOLS` deliberately contains only math capabilities, since only the math agent binds it.
- **WHY not auto-discover tools (e.g. scan the module):** an explicit list is greppable, order-stable, and lets you exclude a tool without deleting it. Auto-discovery would be "clever" but make the agent's capability set implicit and reorder-sensitive to import order.

## Block 3 — `__all__` (lines 29–43)

```python
__all__ = ["MATH_TOOLS", "calculator", "solve_equation", ...]
```

- **WHAT:** Declares the package's public surface.
- **WHY list the individual tools too, not just `MATH_TOOLS`:** it allows targeted imports (a test importing just `is_prime`, or a future history/other agent binding a different subset) without reaching into submodules. `__all__` also documents intent and controls `from app.tools import *`.

---

## Why this shape (tie-back)

The math agent (doc 09) is only as capable as this list. Because `MATH_TOOLS` is the one
source of truth, the agent's *advertised* tools (bound to the LLM so it knows what it can
call) and its *executable* tools (the `ToolNode` that actually runs the calls) can never
drift apart — a mismatch there would be a runtime failure where the model calls a tool the
graph can't execute. This registry is the small but load-bearing guarantee that they stay
identical.

Next: [08-chain-base](08-chain-base.md) — leaving tools for the specialists: the `BaseChain` contract they all implement. →
