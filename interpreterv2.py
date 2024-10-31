from typing import Optional, Any
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
import json, sys


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
        self.variable_name_to_value = {}  # dict to hold variables
        self.run_func(self.get_func_node("main"), [])

    def get_func_node(self, name: str) -> Optional[Element]:
        """
        Gets the main func node of the program. Returns None if no func node.
        """
        assert isinstance(self.ast, Element)
        try:
            functions = self.ast.get("functions")
            for elem in functions:
                if elem.get("name") == name:
                    return elem
            return None
        except AttributeError:
            super().error(ErrorType.NAME_ERROR, f"Missing function definition for '{name}' function")

    def get_target_variable_name(self, statement_node: Element) -> str:
        """
        Gets the target variable of an expression. Function call names do not reference variables.
        """
        # TODO: need check if in scope
        assert statement_node.elem_type in ["vardef", "=", "var"]
        return statement_node.get("name")

    def var_name_exists(self, target_var_name: str) -> bool:
        assert isinstance(target_var_name, str)
        return target_var_name in self.variable_name_to_value

    def run_func(self, func_node: Element, evaluated_args: list) -> None:
        """
        Runs a function
        """
        assert isinstance(func_node, Element)
        assert func_node.elem_type == "func"
        # TODO: if func_node
        # match the args, if no match, typeerror
        # perform lexical scoping
        # need modify do def and var_name_exists
        # some kind of scoping data structure (list?)

        for statement_node in func_node.get("statements"):
            self.run_statement(statement_node)
        # TODO: return value?

    def is_definition(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "vardef"

    def do_definition(self, statement_node: Element) -> None:
        target_var = self.get_target_variable_name(statement_node)
        if self.var_name_exists(target_var):
            super().error(ErrorType.NAME_ERROR, f"Multiple definition of variable '{target_var}'")
        self.variable_name_to_value[target_var] = None

    def is_assignment(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "="

    def do_assignment(self, statement_node: Element) -> None:
        target_var_name = self.get_target_variable_name(statement_node)
        if not self.var_name_exists(target_var_name):
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")
        source_node = self.get_expression_node(statement_node)
        resulting_value = self.evaluate_expression(source_node)
        self.variable_name_to_value[target_var_name] = resulting_value

    def is_func_call(self, statement_node: Element) -> bool:
        return statement_node.elem_type == "fcall"

    def do_func_call(self, statement_node: Element) -> Any:
        """
        Must return the return value of the fcall
        """
        evaluated_args = [self.evaluate_expression(x) for x in statement_node.get("args")]
        match statement_node.get("name"):
            case "inputi":
                match len(evaluated_args):
                    case 1:
                        super().output(str(evaluated_args[0]))
                    case 0:
                        pass
                    case other:
                        super().error(ErrorType.TYPE_ERROR, f"Function inputi expected 0 or 1 arguments, got {other}")
                return int(super().get_input())
            case "print":
                super().output("".join([str(x) for x in evaluated_args]))
            case other:
                # Check for function definition
                self.run_func(self.get_func_node(other), evaluated_args)

    def run_statement(self, statement_node) -> None:
        assert isinstance(statement_node, Element)
        if self.is_definition(statement_node):
            self.do_definition(statement_node)
        elif self.is_assignment(statement_node):
            self.do_assignment(statement_node)
        elif self.is_func_call(statement_node):
            self.do_func_call(statement_node)

    def get_expression_node(self, statement_node: Element) -> Element:
        """
        Gets the expression node of a statement.
        NOTE: Only assignment statements have an expression member, but this does not mean that an expression can only appear in the expression member of a statement
        """
        assert statement_node.elem_type == "="
        return statement_node.get("expression")

    def is_value_node(self, expression_node: Element) -> bool:
        """
        A value node is a constant
        """
        return "val" in expression_node.dict

    def is_variable_node(self, expression_node: Element) -> bool:
        return expression_node.elem_type == "var"

    def is_binary_operator(self, expression_node: Element) -> bool:
        return "op1" in expression_node.dict and "op2" in expression_node.dict

    def get_value_of_variable(self, variable_node: Element) -> Any:
        target_var_name = self.get_target_variable_name(variable_node)
        try:
            return self.variable_name_to_value[target_var_name]
        except KeyError:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")

    def get_value(self, value_node: Element) -> Any:
        return value_node.get("val")

    def evaluate_binary_operator(self, expression_node: Element) -> Any:
        """
        Probably need some error checking to see if they're the same type. Needs to evaluate the values of the individual operands first.
        """
        op1, op2 = [self.evaluate_expression(expression_node.get(x)) for x in ["op1", "op2"]]
        try:
            match expression_node.elem_type:
                case "+":
                    return op1 + op2
                case "-":
                    return op1 - op2
        except TypeError as e:
            super().error(ErrorType.TYPE_ERROR, str(e))

    def evaluate_expression(self, expression_node: Element) -> Any:
        if self.is_value_node(expression_node):
            return self.get_value(expression_node)
        elif self.is_variable_node(expression_node):
            return self.get_value_of_variable(expression_node)
        elif self.is_binary_operator(expression_node):
            return self.evaluate_binary_operator(expression_node)
        elif self.is_func_call(expression_node):
            return self.do_func_call(expression_node)


def main():
    with open("test_program.brew", "r") as file:
        program = file.read()
    Interpreter().run(program)
    # print(ast := parse_program(program))
    # json.dump(json.loads("{"+str(ast)+"}"), sys.stdout, indent=4)


if __name__ == "__main__":
    main()
