from typing import Callable, Optional


class Value:
    """
    Value object. Has a type and stores data.
    Struct types store their data in dict form.
    Kind of like a scope.
    """
    def __init__(self, type: Optional[str], data: Optional[dict[str, "Value"] | str | int | bool]):
        self.type = type
        self.data = data

    def __str__(self):
        match self.type:
            case "bool":
                return str(self.data).lower()
            case "int" | "string":
                return str(self.data)
            case _:
                return str(self.data) if self.data is not None else "nil"


BINARY_OPERATORS: dict[tuple[str, str], dict[str, Callable[[Value, Value], Value]]] = {
    ("bool", "bool"): {
        "||": lambda a, b: Value("bool", a.data or b.data),
        "&&": lambda a, b: Value("bool", a.data and b.data),
        "==": lambda a, b: Value("bool", a.data == b.data),
        "!=": lambda a, b: Value("bool", a.data != b.data)
    },
    ("bool", "int"): {
        "||": lambda a, b: Value("bool", bool(a.data) or bool(b.data)),
        "&&": lambda a, b: Value("bool", bool(a.data) and bool(b.data)),
        "==": lambda a, b: Value("bool", bool(a.data) == bool(b.data)),
        "!=": lambda a, b: Value("bool", bool(a.data) != bool(b.data))
    },
    ("bool", "string"): {
        "==": lambda a, b: Value("bool", False),
        "!=": lambda a, b: Value("bool", True)
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
        "!=": lambda a, b: Value("bool", a.data != b.data),
        "&&": lambda a, b: Value("bool", bool(a.data) and bool(b.data)),
        "||": lambda a, b: Value("bool", bool(a.data) or bool(b.data))
    },
    ("int", "string"): {
        "==": lambda a, b: Value("bool", False),
        "!=": lambda a, b: Value("bool", True)
    },
    ("nil", "nil"): {
        "==": lambda a, b: Value("bool", True),
        "!=": lambda a, b: Value("bool", False)
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
        "!=": lambda a, b: Value("bool", not(a is b or (a.data is None and b.data is None)))
    }
}


PRIMITIVES = {
    "bool",
    "int",
    "string"
}


UNARY_OPERATORS: dict[str, dict[str, Callable[[Value], Value]]] = {
    "bool": {
        "!": lambda a: Value("bool", not a.data)
    },
    "int": {
        "!": lambda a: Value("bool", not a.data),
        "neg": lambda a: Value("int", -a.data)
    }
}


def get_binary_operator(op1: Value, op2: Value, op: str) -> Optional[Callable[[Value, Value], Value]]:
    type1 = "nil" if op1.type is None else "struct" if op1.type not in PRIMITIVES else op1.type
    type2 = "nil" if op2.type is None else "struct" if op2.type not in PRIMITIVES else op2.type
    if type2 == "struct" and type1 == "struct" and op1.type != op2.type:
        return None
    sorted_types = tuple(sorted([type1, type2]))
    if sorted_types not in BINARY_OPERATORS or op not in BINARY_OPERATORS[sorted_types]:
        return None
    return BINARY_OPERATORS[sorted_types][op]


def get_unary_operator(op1: Value, op: str) -> Optional[Callable[[Value], Value]]:
    if op1.type not in UNARY_OPERATORS or op not in UNARY_OPERATORS[op1.type]:
        return None
    return UNARY_OPERATORS[op1.type][op]
