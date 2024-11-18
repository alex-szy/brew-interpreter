from typing import Optional, Literal
from element import Element
from utils import Value
from intbase import ErrorType


class ScopeManager:
    """
    Manager for function level and block level scoping.
    """
    def __init__(self) -> None:
        """
        Initialize the stack of scopes.
        Each scope is a tuple of type (bool, dict)
        The bool indicates whether this is a function-level scope or block-level scope
        The dict contains mappings to all the variables in that scope
        """
        self.scopes: list[tuple[bool, dict[str, Value]]] = []

    def push(self, func_level: bool, scope: Optional[dict] = None) -> None:
        """
        Method to call when entering a new scope.

        args:
            `func_level`: bool indicating whether this is a function level or block level scope
            `scope`: optional dict containing the variables in the new scope (use for function parameters)
        """
        if scope is None:
            self.scopes.append((func_level, {}))
        else:
            self.scopes.append((func_level, scope))

    def pop(self) -> None:
        """
        Pops the last scope layer. Call when finishing execution of a block of statements.
        """
        self.scopes.pop()

    def def_var(self, name: str, template: str | Element) -> bool:
        """
        Check if variable defined in current scope. Return false if defined.
        Else define the variable and return true.
        """
        _, scope = self.scopes[-1]
        if name in scope:
            return False
        scope[name] = Value(template)
        return True

    def get_var(self, name: str) -> Value | tuple[ErrorType, str]:
        """
        Iterate in reverse through the stack to find the variable.
        Stop when run out of scopes or when hit function-level scope.
        Either returns a value or raises a KeyError.
        """
        i = iter(name.split("."))
        var_name = next(i)
        for func_level, scope in reversed(self.scopes):
            if var_name in scope:
                target = scope[var_name]
                break
            if func_level:
                return ErrorType.NAME_ERROR, f"Undefined variable: {var_name}"
        for name in i:
            if hasattr(target, "template"): # is a struct
                if target.data is None:
                    return ErrorType.FAULT_ERROR, f"Attempted to access field {name} of uninitialized struct {var_name}"
                if name not in target.data:
                    return ErrorType.NAME_ERROR, f"Variable {var_name} has no field {name}"
                target = target.data[name]
            else:
                return ErrorType.TYPE_ERROR, f"Not a struct: {var_name}"
        return target

    def set_var(self, name: str, val: Value) -> Literal[True] | tuple[ErrorType, str]:
        """
        Same algorithm as get_var.
        Either sets the variable or raises KeyError if variable not found.
        """
        i = iter(name.split("."))
        var_name = next(i)
        for func_level, scope in reversed(self.scopes):
            if var_name in scope:
                # found the variable
                # if no dot operator, assign immediately and return true
                try:
                    target = scope[var_name]
                    name = next(i)
                    break
                except StopIteration:
                    scope[var_name] = val
                    return True
            if func_level:
                return ErrorType.NAME_ERROR, f"Undefined variable: {var_name}"
            
        # check whether variable is struct
        if not hasattr(target, "template"):
            return ErrorType.TYPE_ERROR, f"Not a struct: {var_name}"
        
        while True:
            if target.data is None:
                return ErrorType.FAULT_ERROR, f"Attempted to access field {name} of uninitialized struct {var_name}"
            if name not in target.data:
                return ErrorType.NAME_ERROR, f"Variable {var_name} has no field {name}"
            try:
                field = next(i)
                target = target.data[name]
                name = field
            except StopIteration:
                target.data[name] = val
                return True
