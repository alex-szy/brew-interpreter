from typing import Optional, Any
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
from utils import BINARY_OPERATORS, UNARY_OPERATORS, ArgumentError
import json


class Interpreter(InterpreterBase):
    """
    TODO: Object references
    """
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def run(self, program: str) -> None:
        """
        Main function invoked by the autograder
        """
        self.ast = parse_program(program)         # parse program into AST
        self.scopes = []  # list of dicts to hold variables in scope
        # get_func_node guaranteed to return list with at least 1 element
        self.run_func(self.get_func_node("main")[0], [])

    def get_func_node(self, name: str) -> list[Element]:
        """
        Gets func node of the program by name. Raise error if function not defined.
        Returns list with at least 1 element, or throws a NAME_ERROR.
        """
        assert isinstance(self.ast, Element)
        functions = self.ast.get("functions")
        funclist = []
        for elem in functions:
            if elem.get("name") == name:
                funclist.append(elem)
        if funclist:
            return funclist
        super().error(ErrorType.NAME_ERROR, f"Function '{name}' is not defined")

    def get_target_variable_name(self, statement_node: Element) -> str:
        """
        Gets the target variable of an expression. Function call names do not reference variables.
        """
        assert statement_node.elem_type in ["vardef", "=", "var"]
        return statement_node.get("name")

    def var_name_exists(self, target_var_name: str) -> bool:
        assert isinstance(target_var_name, str)
        return target_var_name in self.scopes[-1]

    def run_func(self, func_node: Element, evaluated_args: list) -> None:
        """
        Runs a function. Creates the scope for the function, runs the statements, then pops the scope and returns the return value.
        """
        assert isinstance(func_node, Element)
        assert func_node.elem_type == "func"
        # perform lexical scoping
        # need modify do def and var_name_exists
        # some kind of scoping data structure (list?)

        # Check for correct number of arguments
        args = func_node.get("args")
        if len(args) != len(evaluated_args):
            raise ArgumentError(f"Function {func_node.get('name')} expected {len(args)} arguments, got {len(evaluated_args)}")

        scope = {arg.get("name"):value for arg, value in zip(args, evaluated_args)}
        self.scopes.append(scope)

        for statement_node in func_node.get("statements"):
            retval, ret = self.run_statement(statement_node)
            if ret:
                self.scopes.pop()
                return retval
        self.scopes.pop()
        return None

    def is_definition(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "vardef"

    def do_definition(self, statement_node: Element) -> None:
        # TODO: needs to handle vardefs in nested if statements
        target_var = self.get_target_variable_name(statement_node)
        if self.var_name_exists(target_var):
            super().error(ErrorType.NAME_ERROR, f"Multiple definition of variable '{target_var}'")
        self.scopes[-1][target_var] = None

    def is_assignment(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "="

    def do_assignment(self, statement_node: Element) -> None:
        target_var_name = self.get_target_variable_name(statement_node)
        if not self.var_name_exists(target_var_name):
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")
        source_node = self.get_expression_node(statement_node)
        resulting_value = self.evaluate_expression(source_node)
        self.scopes[-1][target_var_name] = resulting_value

    def is_func_call(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "fcall"

    def string_repr(self, x: Any) -> str:
        """
        Returns the string representation to print out for values
        """
        match x:
            case bool():
                return str(x).lower()
            case None:
                return "nil"
            case _:
                return str(x)

    def do_func_call(self, statement_node: Element) -> Any:
        """
        Must return the return value of the fcall
        """
        evaluated_args = [self.evaluate_expression(x) for x in statement_node.get("args")]
        name = statement_node.get("name")
        if name == "inputi" or name == "inputs":
            match len(evaluated_args):
                case 0:
                    pass
                case 1:
                    super().output(str(evaluated_args[0]))
                case other:
                    super().error(ErrorType.NAME_ERROR, f"Function inputi expected 0 or 1 arguments, got {other}")
            return int(super().get_input()) if name == "inputi" else super().get_input() # maybe need to throw an error here?                
        elif name == "print":
            super().output("".join([self.string_repr(x) for x in evaluated_args]))
        else:
            for func in self.get_func_node(name):
                # get_func_node guaranteed to return at least 1 element list
                try:
                    return self.run_func(func, evaluated_args)
                except ArgumentError as e:
                    # wrong number of arguments
                    error = e
            super().error(ErrorType.NAME_ERROR, str(error))

    def is_return_statement(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "return"
    
    def do_return_statement(self, statement_node: Element) -> Any:
        return self.evaluate_expression(self.get_expression_node(statement_node))

    def run_statement(self, statement_node) -> tuple[Any, bool]:
        assert isinstance(statement_node, Element)
        retval, ret = None, False
        if self.is_definition(statement_node):
            self.do_definition(statement_node)
        elif self.is_assignment(statement_node):
            self.do_assignment(statement_node)
        elif self.is_func_call(statement_node):
            self.do_func_call(statement_node)
        elif self.is_return_statement(statement_node):
            retval = self.do_return_statement(statement_node)
            ret = True
        return retval, ret
            

    def get_expression_node(self, statement_node: Element) -> Element:
        """
        Gets the expression node of a statement.
        """
        assert statement_node.elem_type in ["=", "return"]
        return statement_node.get("expression")

    def is_value_node(self, expression_node: Element) -> bool:
        """
        A value node is a constant
        """
        return "val" in expression_node.dict or expression_node.elem_type == "nil"

    def is_variable_node(self, expression_node: Element) -> bool:
        return expression_node.elem_type == "var"

    def is_binary_operator(self, expression_node: Element) -> bool:
        return "op1" in expression_node.dict and "op2" in expression_node.dict
    
    def is_unary_operator(self, expression_node: Element) -> bool:
        return "op1" in expression_node.dict and "op2" not in expression_node.dict

    def get_value_of_variable(self, variable_node: Element) -> Any:
        target_var_name = self.get_target_variable_name(variable_node)
        try:
            return self.scopes[-1][target_var_name]
        except KeyError:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")

    def get_value(self, value_node: Element) -> Any:
        val = value_node.get("val")
        match value_node.elem_type:
            case "nil":
                return None
            case "bool":
                return bool(val)
            case _:
                return val

    def evaluate_binary_operator(self, expression_node: Element) -> Any:
        """
        Probably need some error checking to see if they're the same type. Needs to evaluate the values of the individual operands first.
        """
        op1, op2 = [self.evaluate_expression(expression_node.get(x)) for x in ["op1", "op2"]]
        try:
            return BINARY_OPERATORS[expression_node.elem_type](op1, op2)
        except TypeError as e:
            super().error(ErrorType.TYPE_ERROR, str(e))

    def evaluate_unary_operator(self, expression_node: Element) -> Any:
        op1 = self.evaluate_expression(expression_node.get("op1"))
        try:
            return UNARY_OPERATORS[expression_node.elem_type](op1)
        except TypeError as e:
            super().error(ErrorType.TYPE_ERROR, str(e))

    def evaluate_expression(self, expression_node: Element) -> Any:
        if self.is_value_node(expression_node):
            return self.get_value(expression_node)
        elif self.is_variable_node(expression_node):
            return self.get_value_of_variable(expression_node)
        elif self.is_binary_operator(expression_node):
            return self.evaluate_binary_operator(expression_node)
        elif self.is_unary_operator(expression_node):
            return self.evaluate_unary_operator(expression_node)
        elif self.is_func_call(expression_node):
            return self.do_func_call(expression_node)


def write_ast_to_json(program):
    with open("ast.json", "w") as outfile:
        json.dump(json.loads("{"+str(parse_program(program))+"}"), outfile, indent=4)


def main():
    with open("program.br", "r") as file:
        program = file.read()
    write_ast_to_json(program)
    Interpreter().run(program)


if __name__ == "__main__":
    main()
