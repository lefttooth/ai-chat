"""
MCP（Model Context Protocol）数学计算服务模块
"""
import ast
import operator
from typing import Optional

def mcp_math_request(query: str) -> dict:
    """
    MCP请求：输入query字符串，返回MCP格式响应。
    """
    # 只允许数字、运算符、括号和空格
    allowed = set('0123456789+-*/().eE ')
    expr = query.replace('等于多少', '').replace('等于几', '').replace('是多少', '').replace('=','').strip()
    if not expr or not all(c in allowed for c in expr):
        return {
            "type": "mcp.math",
            "status": "not_applicable",
            "result": None,
            "reason": "not a math expression"
        }
    try:
        node = ast.parse(expr, mode='eval')
        def eval_(n):
            if isinstance(n, ast.Expression):
                return eval_(n.body)
            elif isinstance(n, ast.BinOp):
                left, right = eval_(n.left), eval_(n.right)
                if isinstance(n.op, ast.Add): return operator.add(left, right)
                if isinstance(n.op, ast.Sub): return operator.sub(left, right)
                if isinstance(n.op, ast.Mult): return operator.mul(left, right)
                if isinstance(n.op, ast.Div): return operator.truediv(left, right)
                if isinstance(n.op, ast.Pow): return operator.pow(left, right)
            elif isinstance(n, ast.UnaryOp):
                if isinstance(n.op, ast.UAdd): return +eval_(n.operand)
                if isinstance(n.op, ast.USub): return -eval_(n.operand)
            elif isinstance(n, ast.Num):
                return n.n
            elif isinstance(n, ast.Constant):
                return n.value
            else:
                raise ValueError('不支持的表达式')
        result = eval_(node)
        return {
            "type": "mcp.math",
            "status": "success",
            "result": result,
            "reason": None
        }
    except Exception as e:
        return {
            "type": "mcp.math",
            "status": "error",
            "result": None,
            "reason": str(e)
        }
