import ast
import operator as op

_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.USub: op.neg, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculate(expression: str):
    """Safe arithmetic evaluator - no eval(), AST-restricted (FR-13 calculator tool)."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return {"ok": True, "result": result, "expression": expression}
    except Exception as e:
        return {"ok": False, "error": str(e), "expression": expression}

def calculate_corrosion_rate(old_thickness: float, new_thickness: float, years_between: float) -> float:
    """Calculate the corrosion rate."""
    if years_between <= 0:
        return 0.0
    rate = (old_thickness - new_thickness) / years_between
    return max(0.0, rate)

def calculate_remaining_life(current_thickness: float, min_thickness: float, corrosion_rate: float) -> float:
    """Calculate the remaining life in years."""
    if corrosion_rate <= 0:
        return float('inf')
    remaining = current_thickness - min_thickness
    if remaining <= 0:
        return 0.0
    return remaining / corrosion_rate
