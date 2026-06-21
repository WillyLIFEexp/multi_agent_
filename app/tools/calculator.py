"""Safe arithmetic calculator tool (AST-based, no eval)."""
import ast
import operator

from langchain_core.tools import tool

# Allowed binary / unary operators -> implementation
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def safe_eval(expression: str) -> float:
    """Evaluate an arithmetic expression safely. Raises ValueError on bad input."""
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression.

    Supports + - * / // % ** and parentheses, e.g. "2 * (3 + 4) ** 2".
    Use this for straightforward numeric computation.
    """
    try:
        return str(safe_eval(expression))
    except Exception as exc:  # noqa: BLE001 - report any parse/eval issue to the LLM
        return f"Error: {exc}"
