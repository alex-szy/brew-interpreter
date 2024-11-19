import json
from typing import Optional
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
from utils import get_binary_operator, get_unary_operator, Value
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
        ast = parse_program(program)         # parse program into AST
        self.do_func_defs(ast)
        del ast
        # get_func_node guaranteed to return list with at least 1 element
        self.run_func(self.get_func_nodes("main")[0], [])

    def do_func_defs(self, ast: Element) -> None:
        """
        Do the function definitions.
        """
        self.funcs: dict[str, list[Element]] = {} # dict which maps name to list of functions
        for elem in ast.get("functions"):
            name = elem.get("name")
            if name in self.funcs:
                self.funcs[name].append(elem)
            else:
                self.funcs[name] = [elem]

    def get_func_nodes(self, name: str) -> list[Element]:
        """
        Gets all func nodes that match `name`. Raise error if none are found.
        Returns list with at least 1 element, or throws a NAME_ERROR.
        """
        if name not in self.funcs:
            super().error(ErrorType.NAME_ERROR, f"Function '{name}' is not defined")
        return self.funcs[name]

    def run_func(self, func_node: Element, evaluated_args: list[Value]) -> tuple[Optional[Value], None] | tuple[None, tuple[ErrorType, str]]:
        """
        Runs a function. Creates the scope for the function, runs the statements, then pops the scope and returns the return value.

        Returns a tuple with an ErrorType and a description of the error if wrong number of parameters was passed.
        """
        # Check for correct number of arguments
        args = func_node.get("args")
        if len(args) != len(evaluated_args):
            return None, (
                ErrorType.NAME_ERROR,
                f"Function {func_node.get('name')} expected {len(args)} arguments, got {len(evaluated_args)}"
            )

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
        return (retval, None)

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
        scope = self.scope_manager.get_scope_of_var(target_var_name)
        if scope is None:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")
        # TODO: Lazy evaluation
        evaluated_expr = self.evaluate_expression(statement_node.get("expression"))
        scope[target_var_name] = evaluated_expr


    def do_func_call(self, statement_node: Element) -> Value:
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
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Function inputi expected 0 or 1 arguments, got {other}"
                    )
            if name == "inputi":
                return Value("int", int(super().get_input()))
            else:
                return Value("string", super().get_input())
        elif name == "print":
            super().output("".join([str(x) for x in evaluated_args]))
            return Value("nil", None)
        else:  # user defined functions
            # try all the functions we find, execute the first one that matches the args
            for func in self.get_func_nodes(name):
                # get_func_node guaranteed to return at least 1 element list
                retval, error = self.run_func(func, evaluated_args)
                if error is None:
                    return Value("nil", None) if retval is None else retval
            err, msg = error
            super().error(err, msg)
            

    def do_if_statement(self, statement_node: Element) -> Optional[Value]:
        """
        Executes an `if` statement.
        1. Evaluate the condition.
        2. Run either one of the 2 statement blocks.
        """
        evaluated_expr = self.evaluate_expression(statement_node.get("condition"))
        if evaluated_expr.type != "bool":
            super().error(ErrorType.TYPE_ERROR, "Expression must be of type 'bool'")

        # Push a block level scope
        self.scope_manager.push(False)
        if evaluated_expr.data:
            retval = self.run_statement_block(statement_node.get("statements"))
        else:
            retval = self.run_statement_block(statement_node.get("else_statements"))
        # Pop the scope we pushed
        self.scope_manager.pop()

        return retval
    
    def do_for_statement(self, statement_node: Element) -> Optional[Value]:
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
            if evaluated_expr.type != "bool":
                super().error(ErrorType.TYPE_ERROR, "Expression must be of type 'bool'")
            if not evaluated_expr.data:
                break

            # Push a block level scope
            self.scope_manager.push(False)
            retval = self.run_statement_block(statement_node.get("statements"))
            # Pop the scope we pushed
            self.scope_manager.pop()

            if self.ret_flag:
                return retval
            self.run_statement(statement_node.get("update"))

    def do_return_statement(self, statement_node: Element) -> Optional[Value]:
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

    def run_statement(self, statement_node: Element) -> Optional[Value]:
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

    def run_statement_block(self, statement_block: list[Element]) -> Optional[Value]:
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

    def get_value(self, value_node: Element) -> Value:
        """
        Get the value of the value node.
        """
        val = value_node.get("val")
        if value_node.elem_type == "nil":
            return Value("nil", None)
        return Value(value_node.elem_type, val)

    def get_value_of_variable(self, variable_node: Element) -> Value:
        """
        Attempt to get the value of a variable.
        Raise an error if variable is not in scope.
        """
        target_var_name = variable_node.get("name")
        scope = self.scope_manager.get_scope_of_var(target_var_name)
        if scope is None:
            super().error(ErrorType.NAME_ERROR, f"Undefined variable '{target_var_name}'")
        return scope[target_var_name]            

    def evaluate_binary_operator(self, expression_node: Element) -> Value:
        """
        Evaluates both operands, then performs the correct binary operation on them.
        """
        op1, op2 = [self.evaluate_expression(expression_node.get(x)) for x in ["op1", "op2"]]
        op = get_binary_operator(op1, op2, expression_node.elem_type)
        if op is None:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Unsupported operand type(s) for binary {expression_node.elem_type}: {op1.type}, {op2.type}"
            )
        return op(op1, op2)

    def evaluate_unary_operator(self, expression_node: Element) -> Value:
        """
        Evaluates the operand then performs the correct unary operation on it
        """
        op1 = self.evaluate_expression(expression_node.get("op1"))
        op = get_unary_operator(op1, expression_node.elem_type)
        if op is None:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Unsupported operand type for unary {expression_node.elem_type}: {op1.type}"
            )
        return op(op1)

    def evaluate_expression(self, expression_node: Element) -> Value:
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
