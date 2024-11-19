from typing import Callable, Optional


class Value:
    """
    Value object. Has a type and stores data.
    """
    def __init__(self, type: str, data: Optional[str | int | bool]):
        self.type = type
        self.data = data

    def __str__(self):
        match self.type:
            case "bool":
                return str(self.data).lower()
            case "int" | "string":
                return str(self.data)
            case "nil":
                return "nil"


BINARY_OPERATORS: dict[tuple[str, str], dict[str, Callable[[Value, Value], Value]]] = {
    ("bool", "bool"): {
        "||": lambda a, b: Value("bool", a.data or b.data),
        "&&": lambda a, b: Value("bool", a.data and b.data),
    },
    ("int", "int"): {
        "+": lambda a, b: Value("int", a.data + b.data),
        "-": lambda a, b: Value("int", a.data - b.data),
        "*": lambda a, b: Value("int", a.data * b.data),
        "/": lambda a, b: Value("int", a.data // b.data),
        ">": lambda a, b: Value("bool", a.data > b.data),
        ">=": lambda a, b: Value("bool", a.data >= b.data),
        "<": lambda a, b: Value("bool", a.data < b.data),
        "<=": lambda a, b: Value("bool", a.data <= b.data)
    },
    ("string", "string"): {
        "+": lambda a, b: Value("string", a.data + b.data),
    }
}

UNARY_OPERATORS: dict[str, dict[str, Callable[[Value], Value]]] = {
    "bool": {
        "!": lambda a: Value("bool", not a.data)
    },
    "int": {
        "neg": lambda a: Value("int", -a.data)
    }
}


def get_binary_operator(op1: Value, op2: Value, op: str) -> Optional[Callable[[Value, Value], Value]]:
    match op:
        case "==":
            return lambda a, b: Value("bool", a.type == b.type and a.data == b.data)
        case "!=":
            return lambda a, b: Value("bool", a.type != b.type or a.data != b.data)
    sorted_types = tuple(sorted([op1.type, op2.type]))
    if sorted_types not in BINARY_OPERATORS or op not in BINARY_OPERATORS[sorted_types]:
        return None
    return BINARY_OPERATORS[sorted_types][op]


def get_unary_operator(op1: Value, op: str) -> Optional[Callable[[Value], Value]]:
    if op1.type not in UNARY_OPERATORS or op not in UNARY_OPERATORS[op1.type]:
        return None
    return UNARY_OPERATORS[op1.type][op]
