import json
from copy import deepcopy
from typing import Optional
from intbase import InterpreterBase, ErrorType
from element import Element
from brewparse import parse_program
from utils import get_binary_operator, get_unary_operator, Value, PRIMITIVES
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
        # run struct definitions
        self.do_struct_defs(ast)
        # run func definitions
        self.do_func_defs(ast)

        del ast
        # get_func_node guaranteed to return list with at least 1 element
        self.run_func(self.get_func_nodes("main")[0], [])

    def do_struct_defs(self, ast: Element) -> None:
        """
        Do the struct definitions and checks the fields if types are valid.
        Raises ErrorType.TYPE_ERROR if not.
        """
        self.structs: dict[str, Value] = {}
        for elem in ast.get("structs"):
            name = elem.get("name")
            self.structs[name] = Value(name, {})
            for field in elem.get("fields"):
                field_name, var_type = field.get("name"), field.get("var_type")
                if not self.type_exists(var_type):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Invalid type for field '{field_name}' in struct '{name}': '{var_type}'"
                    )
                self.structs[name].data[field_name] = self.default_value(var_type)

    def do_func_defs(self, ast: Element) -> None:
        """
        Do the function definitions and checks for return types.
        Raises ErrorType.TYPE_ERROR if a function definition has no return type or has an invalid argument type.
        """
        self.funcs: dict[str, list[Element]] = {} # dict which maps name to list of functions
        for elem in ast.get("functions"):
            name = elem.get("name")
            ret_type = elem.get("return_type")
            if ret_type is None:
                super().error(ErrorType.TYPE_ERROR, f"Function '{name}' missing return type")
            if ret_type != "void" and not self.type_exists(ret_type):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid return type for function '{name}': '{ret_type}'"
                )
            for arg in elem.get("args"):
                var_type = arg.get("var_type")
                if not self.type_exists(var_type):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Invalid argument type for argument '{arg.get('name')}' in function '{name}': '{var_type}'"
                    )
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
    
    def coerce(self, val: Value, dest_type: str, throw: bool) -> Value | tuple[ErrorType, str]:
        """
        Attempt to coerce a Value to the destination type.
        Return the new Value on success.
        On failure, if throw is True, call super().error immediately.
        Else return a tuple containing the error and description.
        """
        if dest_type == "bool" and val.type in ["int", "bool"]:
            return Value("bool", bool(val.data))
        if val.type is None and dest_type in self.structs:
            return self.default_value(dest_type)
        error = (
            ErrorType.TYPE_ERROR,
            f"Unable to convert value '{str(val)}' of type '{val.type}' to type '{dest_type}'"
        )
        if throw:
            super().error(*error)
        else:
            return error

    def default_value(self, type: str) -> Value:
        """
        Returns the default value given a type.
        """
        if type in self.structs:
            return Value(type, None)
        match type:
            case "string":
                return Value("string", "")
            case "int":
                return Value("int", 0)
            case "bool":
                return Value("bool", False)

    def run_func(self, func_node: Element, evaluated_args: list[Value]) -> Optional[Value | tuple[ErrorType, str]]:
        """
        Runs a function. Creates the scope for the function, runs the statements, then pops the scope and returns the return value.

        Returns a tuple containing an ErrorType and a description of the error, if either the number of arguments is wrong, or the arguments cannot be coerced to the correct type.
        Returns None if the function has a void return type.
        Returns a Value otherwise.
        """
        # Check for correct number of arguments
        args: list[Element] = func_node.get("args")
        if len(args) != len(evaluated_args):
            return ErrorType.NAME_ERROR, f"Function {func_node.get('name')} expected {len(args)} arguments, got {len(evaluated_args)}"
        
        
        # Push a func level scope for the arguments
        self.scope_manager.push(True)
        for arg, value in zip(args, evaluated_args):
            name, var_type = arg.get("name"), arg.get("var_type")
            # Attempt to coerce all arguments to the correct type
            if var_type != value.type:
                value = self.coerce(value, var_type, False)
                if isinstance(value, tuple):
                    # Clean up the scope on error
                    self.scope_manager.pop()
                    return value
            # Define the arguments in scope
            self.scope_manager.def_var(name, value)

        # Push a block level scope for the function body
        self.scope_manager.push(False)
        retval = self.run_statement_block(func_node.get("statements"))
        # Pop the 2 scopes we pushed for the function
        self.scope_manager.pop()
        self.scope_manager.pop()
        self.ret_flag = False
        
        # TODO: check for exception flag

        # Check the return value of the function for a valid type
        ret_type = func_node.get("return_type")
        if ret_type == "void":
            if retval is not None:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to return non-void value in void function {func_node.get('name')}: {str(retval)}"
                )
        else:
            if retval is None:
                # No explicit return statement, or used return without expr
                retval = self.default_value(ret_type)
            elif retval.type != ret_type:
                retval = self.coerce(retval, ret_type, True)
        return retval
    
    def type_exists(self, type: str) -> bool:
        """
        Returns true if the specified type is a primitive, or a user-defined struct.
        Returns false otherwise.
        """
        return type in PRIMITIVES or type in self.structs

    def do_definition(self, statement_node: Element) -> None:
        """
        Attempt a variable definition. Raise an error if it fails.
        """
        target_var, var_type = statement_node.get("name"), statement_node.get("var_type")
        if not self.type_exists(var_type):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Invalid type for '{target_var}': '{var_type}'"
            )
        if not self.scope_manager.def_var(target_var, self.default_value(var_type)):
            super().error(
                ErrorType.NAME_ERROR,
                f"Multiple definition of variable '{target_var}'"
            )

    def get_target_dict(self, name: str) -> tuple[dict[str, Value], str]:
        """
        Using the name, attempt to find the variable, and if it's a struct, attempt to find the dict containing the requested value. Returns the dict and the final name used to index the dict and find the value. You can either use the name to reassign the value, or simply return it.
        """
        targets = name.split(".")
        context = targets[0:1]
        scope = self.scope_manager.get_scope_of_var(context[-1])
        if scope is None:
            super().error(
                ErrorType.NAME_ERROR,
                f"Undefined variable '{context[-1]}'"
            )
        for field in targets[1:]:
            curr = scope[context[-1]]
            var_type = curr.type
            if var_type not in self.structs:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Variable '{'.'.join(context)}' is not a struct type"
                )
            elif curr.data is None:
                super().error(
                    ErrorType.FAULT_ERROR,
                    f"Attempted to dereference an uninitialized struct '{'.'.join(context)}' of type '{var_type}'"
                )
            elif field not in curr.data:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Struct '{'.'.join(context)}' of type '{var_type}' has no field '{field}'"
                )
            context.append(field)
            scope = curr.data
        return scope, context[-1]
    
    def do_assignment(self, statement_node: Element) -> None:
        """
        Attempt to do an assignment. Raise an error if it fails.
        """
        scope, target_var_name = self.get_target_dict(statement_node.get("name"))
        evaluated_expr = self.evaluate_expression(statement_node.get("expression"))
        dest_type = scope[target_var_name].type
        if evaluated_expr.type != dest_type:
            evaluated_expr = self.coerce(evaluated_expr, dest_type, True)
        scope[target_var_name] = evaluated_expr      

    def do_func_call(self, statement_node: Element) -> Optional[Value]:
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
            match name:
                case "inputi":
                    return Value("int", int(super().get_input()))
                case "inputs":
                    return Value("string", super().get_input())
        elif name == "print":
            super().output("".join([str(x) for x in evaluated_args]))
        else:  # user defined functions
            # try all the functions we find, execute the first one that matches the args
            for func in self.get_func_nodes(name):
                # get_func_node guaranteed to return at least 1 element list
                result = self.run_func(func, evaluated_args)
                if not isinstance(result, tuple):
                    return result
            super().error(*result)

    def do_if_statement(self, statement_node: Element) -> Optional[Value]:
        """
        Executes an `if` statement.
        1. Evaluate the condition.
        2. Run either one of the 2 statement blocks.
        """
        evaluated_expr = self.evaluate_expression(statement_node.get("condition"))
        if evaluated_expr.type != "bool":
            evaluated_expr = self.coerce(evaluated_expr, "bool", True)

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
                evaluated_expr = self.coerce(evaluated_expr, "bool", True)
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
            return Value(None, None)
        return Value(value_node.elem_type, val)

    def get_value_of_variable(self, variable_node: Element) -> Value:
        """
        Attempt to get the value of a variable.
        Raise an error if variable is not in scope.
        """
        scope, target_var_name = self.get_target_dict(variable_node.get("name"))
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

    def init_new_struct(self, struct_type: str) -> Value:
        """
        Given a type, return an initialized struct.
        """
        if struct_type not in self.structs:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Undefined struct type '{struct_type}'"
            )
        return deepcopy(self.structs[struct_type])

    def evaluate_expression(self, expression_node: Element) -> Value:
        if "val" in expression_node.dict or expression_node.elem_type == "nil":
            return self.get_value(expression_node)
        elif expression_node.elem_type == "var":
            return self.get_value_of_variable(expression_node)
        elif "op1" in expression_node.dict:
            if "op2" in expression_node.dict:
                return self.evaluate_binary_operator(expression_node)
            else:
                return self.evaluate_unary_operator(expression_node)
        elif expression_node.elem_type == "fcall":
            retval = self.do_func_call(expression_node)
            if retval is None:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to evaluate void expression"
                )
            return retval
        elif expression_node.elem_type == "new":
            var_type = expression_node.get("var_type")
            return self.init_new_struct(var_type)
        


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
