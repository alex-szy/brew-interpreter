from typing import Optional
from utils import Value


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

    def def_var(self, name: str, val: Value) -> bool:
        """
        Check if variable defined in current scope. Return false if defined.
        Else define the variable and return true.
        """
        _, scope = self.scopes[-1]
        if name in scope:
            return False
        scope[name] = val
        return True

    def get_scope_of_var(self, name: str) -> Optional[dict[str, Value]]:
        """
        Iterate in reverse through the stack to find the variable.
        Stop when run out of scopes or when hit function-level scope.
        Returns None if variable not found
        """
        for func_level, scope in reversed(self.scopes):
            if name in scope:
                return scope
            if func_level:
                break
        return None
