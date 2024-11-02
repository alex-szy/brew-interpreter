import operator as o
from typing import Callable, Any, Optional


class ArgumentError(Exception):
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

def _make_logical_typechecked(op) -> bool:
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


class ScopeManager:
    """
    Manager for function level and block level scoping.
    """
    def __init__(self):
        """
        Initialize the stack of scopes.
        Each scope is a tuple of type (bool, dict)
        The bool indicates whether this is a function-level scope or block-level scope
        The dict contains mappings to all the variables in that scope
        """
        self.scopes: list[tuple[bool, bool, dict]] = []

    def push(self, func_level: bool, scope: Optional[dict]=None):
        """
        Method to call when entering a new scope, whether function level or block level
        """
        if scope is None:
            self.scopes.append((func_level, {}))
        else:
            self.scopes.append((func_level, scope))

    def pop(self):
        """
        Method to call when exiting any scope
        """
        self.scopes.pop()

    def vardef(self, name: str) -> bool:
        """
        Check if variable defined in current scope.
        """
        _, scope = self.scopes[-1]
        if name in scope:
            return False
        scope[name] = None
        return True
    
    def get_var(self, name: str) -> Any:
        """
        Iterate in reverse through the stack to find the variable.
        Stop when run out of scopes or when hit function-level scope.
        Either returns a value or raises a KeyError
        """
        for i in range(len(self.scopes)-1, -1, -1):
            func_level, scope = self.scopes[i]
            if name in scope:
                return scope[name]
            if func_level:
                break
        raise KeyError(name)
    
    def set_var(self, name: str, val: Any) -> None:
        """
        Same as get_var. Raises KeyError if variable not found, else sets the variable
        """
        for i in range(len(self.scopes)-1, -1, -1):
            func_level, scope = self.scopes[i]
            if name in scope:
                scope[name] = val
                return
            if func_level:
                break
        raise KeyError(name)
