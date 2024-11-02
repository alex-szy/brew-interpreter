from typing import Optional, Any


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
        self.scopes: list[tuple[bool, bool, dict]] = []

    def push(self, func_level: bool, scope: Optional[dict]=None) -> None:
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

    def vardef(self, name: str) -> bool:
        """
        Check if variable defined in current scope. Return false if defined. Else define the variable and return true.
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
        Same algorithm as get_var. Raises KeyError if variable not found, else sets the variable
        """
        for i in range(len(self.scopes)-1, -1, -1):
            func_level, scope = self.scopes[i]
            if name in scope:
                scope[name] = val
                return
            if func_level:
                break
        raise KeyError(name)
