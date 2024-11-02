from typing import Any
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
from utils import BINARY_OPERATORS, UNARY_OPERATORS, ArgumentError
from scope_manager import ScopeManager
import json


class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def run(self, program: str) -> None:
        """
        Main function invoked by the autograder
        """
        self.ast = parse_program(program)         # parse program into AST
        self.scope_manager = ScopeManager()
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

    def run_func(self, func_node: Element, evaluated_args: list) -> None:
        """
        Runs a function. Creates the scope for the function, runs the statements, then pops the scope and returns the return value.

        Raises an ArgumentError if wrong number of parameters was passed.
        """
        assert isinstance(func_node, Element)
        assert func_node.elem_type == "func"

        # Check for correct number of arguments
        args = func_node.get("args")
        if len(args) != len(evaluated_args):
            raise ArgumentError(f"Function {func_node.get('name')} expected {len(args)} arguments, got {len(evaluated_args)}")

        scope = {arg.get("name"): value for arg, value in zip(args, evaluated_args)}
        # Push a func level scope into the scope manager
        self.scope_manager.push(True, scope)
        retval, _ = self.run_statement_block(func_node.get("statements"))
        self.scope_manager.pop()
        return retval

    def do_definition(self, statement_node: Element) -> None:
        """
        Attempt a variable definition. Raise an error if it fails.
        """
        target_var = self.get_target_variable_name(statement_node)
        if not self.scope_manager.vardef(target_var):
            super().error(ErrorType.NAME_ERROR, f"Multiple definition of variable '{target_var}'")

    def do_assignment(self, statement_node: Element) -> None:
        """
        Attempt to do an assignment. Raise an error if it fails.
        """
        target_var_name = self.get_target_variable_name(statement_node)
        try:
            self.scope_manager.set_var(target_var_name, self.evaluate_expression(statement_node.get("expression")))
        except KeyError:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")

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
        Execute a function call statement. The call can either be to a builtin function or a user-defined one.
        For user-defined functions, attempts to call run_func on all functions which match the name. If none match, raise an error.
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
            return int(super().get_input()) if name == "inputi" else super().get_input()  # maybe need to throw an error here?
        elif name == "print":
            super().output("".join([self.string_repr(x) for x in evaluated_args]))
        else:  # user defined functions
            # try all the functions we find, execute the first one that matches the args
            for func in self.get_func_node(name):
                # get_func_node guaranteed to return at least 1 element list
                try:
                    return self.run_func(func, evaluated_args)
                except ArgumentError as e:
                    # wrong number of arguments
                    error = e
            super().error(ErrorType.NAME_ERROR, str(error))

    def run_statement(self, statement_node: Element) -> tuple[Any, bool]:
        """
        Runs a single statement.

        returns:
            `retval`: the return value of the statement, if any
            `ret`: whether or not this statement is, or contains a nested return statement

        Only if and for statements can possibly contain nested return statements.
        """
        match statement_node.elem_type:
            case "vardef":
                self.do_definition(statement_node)
            case "=":
                self.do_assignment(statement_node)
            case "fcall":
                self.do_func_call(statement_node)
            case "if":
                expr = self.evaluate_expression(statement_node.get("condition"))
                if not isinstance(expr, bool):
                    super().error(ErrorType.TYPE_ERROR, "Expression in if statement must be of type 'bool'")

                self.scope_manager.push(False)
                if expr:
                    retval, ret = self.run_statement_block(statement_node.get("statements"))
                else:
                    retval, ret = self.run_statement_block(statement_node.get("else_statements"))
                self.scope_manager.pop()

                return retval, ret
            case "for":
                self.run_statement(statement_node.get("init"))
                while True:
                    expr = self.evaluate_expression(statement_node.get("condition"))
                    if not isinstance(expr, bool):
                        super().error(ErrorType.TYPE_ERROR, "Expression in if statement must be of type 'bool'")
                    if not expr:
                        break

                    self.scope_manager.push(False)
                    retval, ret = self.run_statement_block(statement_node.get("statements"))
                    self.scope_manager.pop()

                    if ret:
                        return retval, True
                    self.run_statement(statement_node.get("update"))
            case "return":
                expr = statement_node.get("expression")
                if expr is None:
                    return None, True
                return self.evaluate_expression(expr), True
            case _:
                raise Exception(f"unsupported statement type: {statement_node.elem_type}")
        return None, False

    def run_statement_block(self, statement_block: list[Element]) -> tuple[Any, bool]:
        """
        Runs a block of statements. If the block contains a (potentially nested) return statement, terminate execution and return the value.
        Else run all the statements and return None.

        returns:
            `retval`: the final return value of the block of statements, if any
            `ret`: whether or not the block contains a return statement
        """
        if statement_block is None:
            return None, False
        for statement_node in statement_block:
            retval, ret = self.run_statement(statement_node)
            if ret:
                return retval, True
        return None, False

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
        """
        Attempt to get the value of a variable. Raise an error if it fails.
        """
        target_var_name = self.get_target_variable_name(variable_node)
        try:
            return self.scope_manager.get_var(target_var_name)
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
        Evaluates both operands, then performs the correct binary operation on them.
        """
        op1, op2 = [self.evaluate_expression(expression_node.get(x)) for x in ["op1", "op2"]]
        try:
            return BINARY_OPERATORS[expression_node.elem_type](op1, op2)
        except TypeError as e:
            super().error(ErrorType.TYPE_ERROR, str(e))

    def evaluate_unary_operator(self, expression_node: Element) -> Any:
        """
        Evaluates the operand then performs the correct unary operation on it
        """
        op1 = self.evaluate_expression(expression_node.get("op1"))
        try:
            return UNARY_OPERATORS[expression_node.elem_type](op1)
        except TypeError as e:
            super().error(ErrorType.TYPE_ERROR, str(e))

    def evaluate_expression(self, expression_node: Element) -> Any:
        if self.is_value_node(expression_node):
            return self.get_value(expression_node)
        if self.is_variable_node(expression_node):
            return self.get_value_of_variable(expression_node)
        if self.is_binary_operator(expression_node):
            return self.evaluate_binary_operator(expression_node)
        if self.is_unary_operator(expression_node):
            return self.evaluate_unary_operator(expression_node)
        if expression_node.elem_type == "fcall":
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
