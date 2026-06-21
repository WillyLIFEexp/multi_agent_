"""Symbolic math tools backed by SymPy."""
import sympy as sp
from langchain_core.tools import tool


def _parse(expr: str) -> sp.Expr:
    # sympify with evaluate keeps expressions symbolic; no arbitrary code runs.
    return sp.sympify(expr)


@tool
def solve_equation(equation: str, variable: str = "x") -> str:
    """Solve an equation for a variable.

    ``equation`` may be like "x**2 - 4" (assumed = 0) or "2*x + 1 = 5".
    Returns the list of solutions.
    """
    try:
        var = sp.Symbol(variable)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            expr = _parse(lhs) - _parse(rhs)
        else:
            expr = _parse(equation)
        solutions = sp.solve(expr, var)
        return str(solutions)
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


@tool
def derivative(expression: str, variable: str = "x", order: int = 1) -> str:
    """Compute the derivative of an expression with respect to a variable."""
    try:
        var = sp.Symbol(variable)
        return str(sp.diff(_parse(expression), var, order))
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


@tool
def integrate(expression: str, variable: str = "x") -> str:
    """Compute the indefinite integral of an expression w.r.t. a variable."""
    try:
        var = sp.Symbol(variable)
        return str(sp.integrate(_parse(expression), var))
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


@tool
def simplify_expr(expression: str) -> str:
    """Algebraically simplify an expression."""
    try:
        return str(sp.simplify(_parse(expression)))
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
