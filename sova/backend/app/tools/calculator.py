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
