# math_tools.py
import json
import ast
import operator as op

# ---------- Safe math expression evaluator ----------
_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}

def _eval_node(node):
    if isinstance(node, ast.Num):  # Py<3.8
        return node.n
    if isinstance(node, ast.Constant):  # Py>=3.8
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_OPS[type(node.op)](left, right)
    if isinstance(node, ast.Expr):
        return _eval_node(node.value)
    raise ValueError("Unsupported expression syntax.")

def _safe_eval_expr(expr: str):
    try:
        tree = ast.parse(expr, mode="eval")
        return {"expression": expr, "result": _eval_node(tree.body), "error": None}
    except Exception as e:
        return {"expression": expr, "result": None, "error": str(e)}

# ---------- Registrar ----------
def register_tools(mcp):
    """
    Register math tools on a provided FastMCP instance.
    Usage:
        from fastmcp import FastMCP
        from math_tools import register_math_tools
        mcp = FastMCP("Math MCP Server")
        register_math_tools(mcp)
    """

    @mcp.tool
    def add(a: float, b: float):
        """Add two numbers and return the sum."""
        return a + b

    @mcp.tool
    def subtract(a: float, b: float):
        """Subtract b from a and return the difference."""
        return a - b

    @mcp.tool
    def multiply(a: float, b: float):
        """Multiply two numbers and return the product."""
        return a * b

    @mcp.tool
    def divide(a: float, b: float):
        """Divide a by b and return the quotient. Raises on division by zero."""
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b

    @mcp.tool
    def calculate(expression: str) -> str:
        """
        Safely evaluate a math expression.
        Supported: +, -, *, /, //, %, **, parentheses, ints/floats, unary +/-.
        Returns a JSON string with expression, result, and error (if any).
        """
        result = _safe_eval_expr(expression)
        return json.dumps(result)
