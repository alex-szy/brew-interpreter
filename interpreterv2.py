import json
from typing import Any
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
from utils import BINARY_OPERATORS, UNARY_OPERATORS, ArgumentError
from scope_manager import ScopeManager


class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        self.scope_manager = ScopeManager()
        self.ret_flag = False

    def run(self, program: str) -> None:
        """
        Main function invoked by the autograder
        """
        self.ast = parse_program(program)         # parse program into AST
        # get_func_node guaranteed to return list with at least 1 element
        self.run_func(self.get_func_nodes("main")[0], [])

    def get_func_nodes(self, name: str) -> list[Element]:
        """
        Gets all func nodes that match `name`. Raise error if none are found.
        Returns list with at least 1 element, or throws a NAME_ERROR.
        """
        functions = self.ast.get("functions")
        funclist = []
        for elem in functions:
            if elem.get("name") == name:
                funclist.append(elem)
        if funclist:
            return funclist
        super().error(ErrorType.NAME_ERROR, f"Function '{name}' is not defined")

    def run_func(self, func_node: Element, evaluated_args: list) -> None:
        """
        Runs a function. Creates the scope for the function, runs the statements, then pops the scope and returns the return value.

        Raises an ArgumentError if wrong number of parameters was passed.
        """
        # Check for correct number of arguments
        args = func_node.get("args")
        if len(args) != len(evaluated_args):
            raise ArgumentError(f"Function {func_node.get('name')} expected {len(args)} arguments, got {len(evaluated_args)}")

        scope = {arg.get("name"): value for arg, value in zip(args, evaluated_args)}
        # Push a func level scope for the arguments
        self.scope_manager.push(True, scope)
        # Push a block level scope for the function body
        self.scope_manager.push(False)
        retval = self.run_statement_block(func_node.get("statements"))
        # Pop the 2 scopes we pushed for the function
        self.scope_manager.pop()
        self.scope_manager.pop()
        self.ret_flag = False
        return retval

    def do_definition(self, statement_node: Element) -> None:
        """
        Attempt a variable definition. Raise an error if it fails.
        """
        target_var = statement_node.get("name")
        if not self.scope_manager.def_var(target_var):
            super().error(ErrorType.NAME_ERROR, f"Multiple definition of variable '{target_var}'")

    def do_assignment(self, statement_node: Element) -> None:
        """
        Attempt to do an assignment. Raise an error if it fails.
        """
        target_var_name = statement_node.get("name")
        evaluated_expr = self.evaluate_expression(statement_node.get("expression"))
        try:
            self.scope_manager.set_var(target_var_name, evaluated_expr)
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
        Execute a function call statement.
        The call can either be to a builtin function or a user-defined one.
        For user-defined functions, attempt to call run_func on all functions which match the name.
        If none match, raise an error.
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
            for func in self.get_func_nodes(name):
                # get_func_node guaranteed to return at least 1 element list
                try:
                    return self.run_func(func, evaluated_args)
                except ArgumentError as e:
                    # wrong number of arguments
                    error = e
            super().error(ErrorType.NAME_ERROR, str(error))

    def do_if_statement(self, statement_node: Element) -> Any:
        """
        Executes an `if` statement.
        1. Evaluate the condition.
        2. Run either one of the 2 statement blocks.
        """
        evaluated_expr = self.evaluate_expression(statement_node.get("condition"))
        if not isinstance(evaluated_expr, bool):
            super().error(ErrorType.TYPE_ERROR, "Expression must be of type 'bool'")

        # Push a block level scope
        self.scope_manager.push(False)
        if evaluated_expr:
            retval = self.run_statement_block(statement_node.get("statements"))
        else:
            retval = self.run_statement_block(statement_node.get("else_statements"))
        # Pop the scope we pushed
        self.scope_manager.pop()

        return retval
    
    def do_for_statement(self, statement_node: Element) -> Any:
        """
        Executes a `for` statement.
        1. Run the init statement. Enter the loop.
        2. Evaluate the condition and break out of the loop if false.
        3. Else, run the statements in the loop.
        4. If the return flag was set, return the value.
        5. Otherwise, run the update statement and repeat the loop.

        It is assumed that the init and update statements will not set the return flag under any circumstances.
        """
        self.run_statement(statement_node.get("init"))
        while True:
            evaluated_expr = self.evaluate_expression(statement_node.get("condition"))
            if not isinstance(evaluated_expr, bool):
                super().error(ErrorType.TYPE_ERROR, "Expression must be of type 'bool'")
            if not evaluated_expr:
                break

            # Push a block level scope
            self.scope_manager.push(False)
            retval = self.run_statement_block(statement_node.get("statements"))
            # Pop the scope we pushed
            self.scope_manager.pop()

            if self.ret_flag:
                return retval
            self.run_statement(statement_node.get("update"))

    def do_return_statement(self, statement_node: Element) -> Any:
        """
        Executes a return statement.
        1. Evaluate the return expression, if there is one.
        2. Set the return flag and return the value.

        It is important that the return flag be set only after the expression is evaluated.
        Otherwise, the function will not finish executing its statements.
        """
        expr = statement_node.get("expression")
        retval = None if expr is None else self.evaluate_expression(expr)
        self.ret_flag = True
        return retval

    def run_statement(self, statement_node: Element) -> Any:
        """
        Runs a single statement.
        """
        match statement_node.elem_type:
            case "vardef":
                self.do_definition(statement_node)
            case "=":
                self.do_assignment(statement_node)
            case "fcall":
                self.do_func_call(statement_node)
            case "if":
                return self.do_if_statement(statement_node)
            case "for":
                return self.do_for_statement(statement_node)
            case "return":
                return self.do_return_statement(statement_node)

    def run_statement_block(self, statement_block: list[Element]) -> Any:
        """
        Runs a block of statements.
        After every statement is executed, check the return flag.
        If it has been set, return the value immediately.
        """
        if statement_block is None:
            return
        for statement_node in statement_block:
            retval = self.run_statement(statement_node)
            if self.ret_flag:
                return retval

    def get_value(self, value_node: Element) -> Any:
        """
        Get the value of the value node.
        """
        val = value_node.get("val")
        match value_node.elem_type:
            case "nil":
                return None
            case "bool":
                return bool(val)
            case _:
                return val

    def get_value_of_variable(self, variable_node: Element) -> Any:
        """
        Attempt to get the value of a variable.
        Raise an error if variable is not in scope.
        """
        target_var_name = variable_node.get("name")
        try:
            return self.scope_manager.get_var(target_var_name)
        except KeyError:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")

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
        if "val" in expression_node.dict or expression_node.elem_type == "nil":
            return self.get_value(expression_node)
        if expression_node.elem_type == "var":
            return self.get_value_of_variable(expression_node)
        if "op1" in expression_node.dict:
            if "op2" in expression_node.dict:
                return self.evaluate_binary_operator(expression_node)
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
