"""Tool registry. Tools are LangChain tools bindable to an LLM."""
from app.tools.calculator import calculator
from app.tools.math_helpers import (
    factorial,
    gcd,
    is_prime,
    lcm,
    mean,
    median,
    square_root,
)
from app.tools.symbolic import derivative, integrate, simplify_expr, solve_equation

MATH_TOOLS = [
    calculator,
    solve_equation,
    derivative,
    integrate,
    simplify_expr,
    square_root,
    factorial,
    gcd,
    lcm,
    is_prime,
    mean,
    median,
]

__all__ = [
    "MATH_TOOLS",
    "calculator",
    "solve_equation",
    "derivative",
    "integrate",
    "simplify_expr",
    "square_root",
    "factorial",
    "gcd",
    "lcm",
    "is_prime",
    "mean",
    "median",
]
