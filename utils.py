import operator as o
from typing import Callable


class ArgumentError(Exception):
    pass


def _make_typechecked(s, op) -> Callable:
    """
    Handles the difference between brewin and python: python allows arithmetic between bool and int, brewin does not.
    """
    def typechecked_op(a, b):
        if bool in (types := {type(a), type(b)}) and int in types:
            raise TypeError(f"unsupported operand type(s) for {s}, '{type(a)}' and '{type(b)}'")
        return op(a, b)
    return typechecked_op


def _make_typechecked_unary(s, op) -> Callable:
    """
    Same as above but for unary operators
    """
    def typechecked_op(a):
        if isinstance(a, bool):
            raise TypeError(f"bad operand type for unary {s}: bool")
        return op(a)
    return typechecked_op


BINARY_OPERATORS = {
    "+": _make_typechecked("+", o.add),
    "-": _make_typechecked("-", o.sub),
    "*": _make_typechecked("*", o.mul),
    "/": _make_typechecked("/", o.floordiv),
    "==": _make_typechecked("==", o.eq),
    "!=": _make_typechecked("!=", o.ne),
    ">": _make_typechecked(">", o.gt),
    ">=": _make_typechecked(">=", o.ge),
    "<": _make_typechecked("<", o.lt),
    "<=": _make_typechecked("<=", o.le),
    "&&": lambda a, b: a and b,
    "||": lambda a, b: a or b
}


UNARY_OPERATORS = {
    "neg": _make_typechecked_unary("-", o.neg),
    "!": o.not_
}
