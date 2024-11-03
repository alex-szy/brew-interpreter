import operator as o
from typing import Callable


class ArgumentError(Exception):
    """
    Custom exception class raised only when function is run with wrong number of args.
    """
    pass


def _both_ops_nobool(s, op) -> Callable:
    """
    Both operands must either be integers or strings
    """
    def typechecked_op(a, b):
        if isinstance(a, bool) or isinstance(b, bool):
            raise TypeError(
                f"unsupported operand type(s) for {s}, '{type(a).__name__}' and '{type(b).__name__}'"
            )
        return op(a, b)
    return typechecked_op


def _both_ops_int(s, op) -> Callable:
    """
    Both operands must be integers
    """
    def typechecked_op(a, b):
        if not type(a) is int or not type(b) is int:
            raise TypeError(
                f"unsupported operand type(s) for {s}, '{type(a).__name__}' and '{type(b).__name__}'"
            )
        return op(a, b)
    return typechecked_op


def _both_ops_bool(s, op) -> Callable:
    """
    Both operands must be booleans
    """
    def typechecked_op(a, b):
        if not isinstance(a, bool) or not isinstance(b, bool):
            raise TypeError(
                f"unsupported operand type(s) for {s}, '{type(a).__name__}' and '{type(b).__name__}'"
            )
        return op(a, b)
    return typechecked_op


def _eq(a, b):
    """
    Both operands must be of the same type to be considered equal.
    """
    if not type(a) is type(b):
        return False
    return a == b


def _ne(a, b):
    """
    Inverse of _eq.
    """
    return not _eq(a, b)


def _neg(a) -> int:
    """
    Operand must be integer.
    """
    if not type(a) is int:
        raise TypeError(
            f"bad operand type for unary negation: {type(a).__name__}"
        )
    return -a


def _not(a) -> bool:
    """
    Operand must be boolean.
    """
    if not isinstance(a, bool):
        raise TypeError(
            f"bad operand type for logical not: {type(a).__name__}"
        )
    return not a


# The 2 dicts below map a string description of operators to their corresponding functions
BINARY_OPERATORS = {
    "+": _both_ops_nobool("+", o.add),
    "-": _both_ops_int("-", o.sub),
    "*": _both_ops_int("*", o.mul),
    "/": _both_ops_int("/", o.floordiv),
    "==": _eq,
    "!=": _ne,
    ">": _both_ops_int(">", o.gt),
    ">=": _both_ops_int(">=", o.ge),
    "<": _both_ops_int("<", o.lt),
    "<=": _both_ops_int("<=", o.le),
    "&&": _both_ops_bool("&&", lambda a, b: a and b),
    "||": _both_ops_bool("||", lambda a, b: a or b)
}


UNARY_OPERATORS = {
    "neg": _neg,
    "!": _not
}
