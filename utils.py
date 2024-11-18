from typing import Callable, Optional
from element import Element


class Value:
    """
    Struct object. Stores a template when first created.
    Dict is None when first created to signify a nil reference.
    """
    def __init__(self, template: str | Element | None= None, val = None):
        assert template in ["bool", "int", "string"] or isinstance(template, Element) or template is None, template
        if isinstance(template, Element):
            self.template = template
            self.type = template.get("name")
        else:
            self.type = template
        if val is None:
            self.data = default_val(self.type)
        else:
            self.data = val

    def __str__(self):
        match self.type:
            case "bool":
                return str(self.data).lower()
            case "int" | "string":
                return str(self.data)
            case _:
                return str(self.data) if self.data is not None else "nil"


def default_val(type: str):
    match type:
        case "bool":
            return False
        case "int":
            return 0
        case "string":
            return ""
        case _:
            return None


def _eq(a: Value, b: Value):
    """
    Both operands must be of the same type to be considered equal.
    """
    if a is b:
        return Value("bool", True)
    if a.data is None and b.data is None and (a.type is None or b.type is None): # both nil values and one of them is a nil literal
        return Value("bool", True)
    if not a.type == b.type:
        return Value("bool", False)
    return Value("bool", a.data == b.data)


BINARY_OPERATORS: dict[tuple[str, str], dict[str, Callable[[Value, Value], Value]]] = {
    ("bool", "bool"): {
        "||": lambda a, b: Value("bool", bool(a.data or b.data)),
        "&&": lambda a, b: Value("bool", bool(a.data and b.data)),
        "==": lambda a, b: Value("bool", a.data == b.data),
        "!=": lambda a, b: Value("bool", a.data != b.data)
    },
    ("bool", "int"): {
        "||": lambda a, b: Value("bool", bool(a.data or b.data)),
        "&&": lambda a, b: Value("bool", bool(a.data and b.data)),
        "==": lambda a, b: Value("bool", bool(a.data) == bool(b.data)),
        "!=": lambda a, b: Value("bool", bool(a.data) != bool(b.data))
    },
    ("bool", "string"): {
        "==": lambda a, b: Value("bool", False),
        "!=": lambda a, b: Value("bool", False)
    },
    ("int", "int"): {
        "+": lambda a, b: Value("int", a.data + b.data),
        "-": lambda a, b: Value("int", a.data - b.data),
        "*": lambda a, b: Value("int", a.data * b.data),
        "/": lambda a, b: Value("int", a.data // b.data),
        ">": lambda a, b: Value("bool", a.data > b.data),
        ">=": lambda a, b: Value("bool", a.data >= b.data),
        "<": lambda a, b: Value("bool", a.data < b.data),
        "<=": lambda a, b: Value("bool", a.data <= b.data),
        "==": lambda a, b: Value("bool", a.data == b.data),
        "!=": lambda a, b: Value("bool", a.data != b.data)
    },
    ("int", "string"): {
        "==": lambda a, b: Value("bool", False),
        "!=": lambda a, b: Value("bool", False)
    },
    ("nil", "nil"): {
        "==": lambda a, b: Value("bool", a.data is b.data),
        "!=": lambda a, b: Value("bool", a.data is not b.data)
    },
    ("nil", "struct"): {
        "==": lambda a, b: Value("bool", a.data is b.data),
        "!=": lambda a, b: Value("bool", a.data is not b.data)
    },
    ("string", "string"): {
        "+": lambda a, b: Value("string", a.data + b.data),
        "==": lambda a, b: Value("bool", a.data == b.data),
        "!=": lambda a, b: Value("bool", a.data != b.data)
    },
    ("struct", "struct"): {
        "==": lambda a, b: Value("bool", a is b or (a.data is None and b.data is None)),
        "!=": lambda a, b: Value("bool", a is not b (a.data is not None or b.data is not None))
    }
}

PRIMITIVES = {
    "bool",
    "int",
    "string"
}


# The 2 dicts below map a string description of operators to their corresponding functions
def get_binary_operator(op1: Value, op2: Value, op: str) -> Optional[Callable[[Value, Value], Value]]:
    type1, type2 = op1.type, op2.type
    if type1 is None:
        type1 = "nil"
    elif type1 not in PRIMITIVES:
        type1 = "struct"
    if type2 is None:
        type2 = "nil"
    elif type2 not in PRIMITIVES:
        type2 = "struct"
    sorted_types = tuple(sorted([type1, type2]))
    if sorted_types not in BINARY_OPERATORS or op not in BINARY_OPERATORS[sorted_types]:
        return None
    return BINARY_OPERATORS[sorted_types][op]


UNARY_OPERATORS: dict[str, dict[str, Callable[[Value], Value]]] = {
    "bool": {
        "!": lambda a: Value("bool", not a.data)
    },
    "int": {
        "!": lambda a: Value("bool", not a.data),
        "neg": lambda a: Value("int", -a.data)
    }
}

def get_unary_operator(op1: Value, op: str) -> Optional[Callable[[Value], Value]]:
    if op1.type not in UNARY_OPERATORS or op not in UNARY_OPERATORS[op1.type]:
        return None
    return UNARY_OPERATORS[op1.type][op]
