import operator as o
from typing import Callable

class ArgumentError(Exception):
    """
    Custom exception class raised only when function is run with wrong number of args.
    """
    pass

def _make_typechecked_nobool(s, op) -> Callable:
    """
    Both operands must either be integers or strings
    """
    def typechecked_op(a, b):
        if isinstance(a, bool) or isinstance(b, bool):
            raise TypeError(f"unsupported operand type(s) for {s}, '{type(a).__name__}' and '{type(b).__name__}'")
        return op(a, b)
    return typechecked_op

def _make_typechecked_int(s, op) -> Callable:
    """
    Both operands must be integers
    """
    def typechecked_op(a, b):
        if not isinstance(a, int) or not isinstance(b, int):
            raise TypeError(f"unsupported operand type(s) for {s}, '{type(a).__name__}' and '{type(b).__name__}'")
        return op(a, b)
    return typechecked_op

def _eq(a, b):
    if not type(a) is type(b):
        return False
    return a == b

def _ne(a, b):
    return not _eq(a, b)

def _neg(a) -> int:
    """
    Operand must be integer
    """
    if not isinstance(a, int):
        raise TypeError(f"bad operand type for unary negation: {type(a).__name__}")
    return -a

def _not(a) -> bool:
    """
    Operand must be boolean
    """
    if not isinstance(a, bool):
        raise TypeError(f"bad operand type for logical not: {type(a).__name__}")
    return not a

def _make_logical_typechecked(op) -> Callable:
    """
    Both operands must be booleans
    """
    def typechecked_op(a, b):
        if not isinstance(a, bool) or not isinstance(b, bool):
            raise TypeError(f"unsupported operand type(s) for &&, '{type(a).__name__}' and '{type(b).__name__}'")
        return op(a, b)
    return typechecked_op


BINARY_OPERATORS = {
    "+": _make_typechecked_nobool("+", o.add),
    "-": _make_typechecked_int("-", o.sub),
    "*": _make_typechecked_int("*", o.mul),
    "/": _make_typechecked_int("/", o.floordiv),
    "==": _eq,
    "!=": _ne,
    ">": _make_typechecked_int(">", o.gt),
    ">=": _make_typechecked_int(">=", o.ge),
    "<": _make_typechecked_int("<", o.lt),
    "<=": _make_typechecked_int("<=", o.le),
    "&&": _make_logical_typechecked(lambda a, b: a and b),
    "||": _make_logical_typechecked(lambda a, b: a or b)
}


UNARY_OPERATORS = {
    "neg": _neg,
    "!": _not
}
