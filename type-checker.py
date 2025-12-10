import json

class TypeChecker:
    def __init__(self):
        # Symbol table: {var_name: {'type': str, 'scope': int}}
        self.symbol_table = {}
        # Function table: {func_name: {'return_type': str, 'params': [(name, type)]}}
        self.function_table = {}
        self.errors = []
        self.warnings = []
        self.scope_level = 0
        
        # Type hierarchy for implicit conversions
        self.type_rank = {
            'bool': 0,
            'char': 1,
            'short': 2,
            'int': 3,
            'long': 4,
            'float': 5,
            'double': 6,
            'string': 7,
            'void': -1
        }
        
        # Operator type compatibility
        self.operator_types = {
            '+': ['int', 'float', 'double', 'long', 'string'],
            '-': ['int', 'float', 'double', 'long'],
            '*': ['int', 'float', 'double', 'long'],
            '/': ['int', 'float', 'double', 'long'],
            '%': ['int', 'long'],
            '==': ['int', 'float', 'double', 'long', 'bool', 'string', 'char'],
            '!=': ['int', 'float', 'double', 'long', 'bool', 'string', 'char'],
            '<': ['int', 'float', 'double', 'long', 'char'],
            '>': ['int', 'float', 'double', 'long', 'char'],
            '<=': ['int', 'float', 'double', 'long', 'char'],
            '>=': ['int', 'float', 'double', 'long', 'char'],
            '&&': ['bool'],
            '||': ['bool'],
            '&': ['int', 'long'],
            '|': ['int', 'long'],
            '^': ['int', 'long'],
            '<<': ['int', 'long'],
            '>>': ['int', 'long'],
        }
    
    def add_error(self, message):
        self.errors.append(f"ERROR: {message}")
    
    def add_warning(self, message):
        self.warnings.append(f"WARNING: {message}")
    
    def enter_scope(self):
        self.scope_level += 1
    
    def exit_scope(self):
        # Remove variables from current scope
        vars_to_remove = [name for name, info in self.symbol_table.items() 
                         if info['scope'] == self.scope_level]
        for name in vars_to_remove:
            del self.symbol_table[name]
        self.scope_level -= 1
    
    def declare_variable(self, name, var_type, scope=None):
        if scope is None:
            scope = self.scope_level
        
        if name in self.symbol_table and self.symbol_table[name]['scope'] == scope:
            self.add_error(f"Variable '{name}' already declared in current scope")
            return False
        
        self.symbol_table[name] = {
            'type': var_type,
            'scope': scope
        }
        return True
    
    def declare_function(self, name, return_type, params):
        if name in self.function_table:
            self.add_error(f"Function '{name}' already declared")
            return False
        
        self.function_table[name] = {
            'return_type': return_type,
            'params': params
        }
        return True
    
    def get_variable_type(self, name):
        if name in self.symbol_table:
            return self.symbol_table[name]['type']
        return None
    
    def infer_type(self, value):
        """Infer type from literal value"""
        if isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, str):
            if value.startswith('"') and value.endswith('"'):
                return 'string'
            # Check if it's a variable reference
            return self.get_variable_type(value)
        elif isinstance(value, bool):
            return 'bool'
        return None
    
    def check_type_compatibility(self, type1, type2):
        """Check if type1 can be assigned to type2"""
        if type1 == type2:
            return True
        
        # Check implicit conversion (widening)
        if type1 in self.type_rank and type2 in self.type_rank:
            if self.type_rank[type1] < self.type_rank[type2]:
                self.add_warning(f"Implicit conversion from '{type1}' to '{type2}'")
                return True
        
        return False
    
    def check_operator_expression(self, expr):
        """Check operator expression and return result type"""
        if not isinstance(expr, dict):
            return self.infer_type(expr)
        
        if expr.get('type') == 'OperatorExpression':
            operator = expr.get('operator')
            identifier = expr.get('identifier')
            value = expr.get('value')
            
            # Get types
            left_type = self.get_variable_type(identifier) if isinstance(identifier, str) else self.infer_type(identifier)
            
            if isinstance(value, dict):
                if value.get('type') == 'FunctionCall':
                    right_type = self.check_function_call(value)
                elif value.get('type') == 'OperatorExpression':
                    right_type = self.check_operator_expression(value)
                else:
                    right_type = self.infer_type(value)
            else:
                right_type = self.infer_type(value)
            
            # Assignment operator
            if operator == '=':                
                if left_type is None:
                    # Check if right side has valid type
                    if right_type is None:
                        self.add_error(f"Cannot assign to '{identifier}': right side has unknown type")
                        return None
                    # Auto-declare variable
                    self.add_warning(f"Variable '{identifier}' used without declaration, auto-declaring as '{right_type}'")
                    self.declare_variable(identifier, right_type)
                    return right_type
                
                if not self.check_type_compatibility(right_type, left_type):
                    self.add_error(f"Type mismatch: cannot assign '{right_type}' to '{left_type}'")
                return left_type
            
            # Other operators
            if operator in self.operator_types:
                valid_types = self.operator_types[operator]
                
                if left_type not in valid_types:
                    self.add_error(f"Operator '{operator}' not valid for type '{left_type}'")
                if right_type not in valid_types:
                    self.add_error(f"Operator '{operator}' not valid for type '{right_type}'")
                
                # Result type
                if operator in ['==', '!=', '<', '>', '<=', '>=', '&&', '||']:
                    return 'bool'
                elif operator in ['+', '-', '*', '/']:
                    # Return wider type
                    if left_type == 'float' or right_type == 'float':
                        return 'float'
                    elif left_type == 'double' or right_type == 'double':
                        return 'double'
                    return 'int'
                else:
                    return left_type
            
            return left_type
        
        return None
    
    def check_function_call(self, call_node):
        """Check function call and return return type"""
        keyword = call_node.get('keyword')
        args = call_node.get('args', [])
        
        # Built-in functions
        if keyword in ['print', 'scan', 'input']:
            return 'void'
        
        # User-defined function
        if keyword not in self.function_table:
            self.add_error(f"Function '{keyword}' not declared")
            return 'void'
        
        func_info = self.function_table[keyword]
        expected_params = func_info['params']
        
        # Check argument count
        if len(args) != len(expected_params):
            self.add_error(f"Function '{keyword}' expects {len(expected_params)} arguments, got {len(args)}")
        
        # Check argument types
        for i, (arg, (param_name, param_type)) in enumerate(zip(args, expected_params)):
            arg_type = self.infer_type(arg)
            if arg_type is None:
                # Variable not found in symbol table
                if isinstance(arg, str) and not arg.startswith('"'):
                    self.add_error(f"Argument {i+1} of function '{keyword}': variable '{arg}' not declared")
                else:
                    self.add_error(f"Argument {i+1} of function '{keyword}': could not determine type")
            elif not self.check_type_compatibility(arg_type, param_type):
                self.add_error(f"Argument {i+1} of function '{keyword}': expected '{param_type}', got '{arg_type}'")
        
        return func_info['return_type']
    
    def check_declaration(self, decl):
        """Check variable declaration"""
        var_type = decl.get('datatype')
        var_name = decl.get('identifier')
        var_value = decl.get('value')
        
        # Normalize datatype to lowercase for consistency
        if var_type:
            var_type = var_type.lower()
        
        # Declare variable
        self.declare_variable(var_name, var_type)
        
        # Check initializer if present
        if var_value is not None:
            if isinstance(var_value, dict):
                if var_value.get('type') == 'OperatorExpression':
                    value_type = self.check_operator_expression(var_value)
                elif var_value.get('type') == 'FunctionCall':
                    value_type = self.check_function_call(var_value)
                else:
                    value_type = self.infer_type(var_value)
            else:
                value_type = self.infer_type(var_value)
            
            if value_type and not self.check_type_compatibility(value_type, var_type):
                self.add_error(f"Cannot initialize '{var_name}' of type '{var_type}' with value of type '{value_type}'")
    
    def check_return_statement(self, return_node, expected_return_type):
        """Check return statement"""
        args = return_node.get('args')
        
        if expected_return_type == 'void':
            if args is not None:
                self.add_error(f"Void function should not return a value")
            return
        
        if args is None:
            self.add_error(f"Function should return a value of type '{expected_return_type}'")
            return
        
        # Check return value type
        if isinstance(args, dict):
            if args.get('type') == 'OperatorExpression':
                return_type = self.check_operator_expression(args)
            elif args.get('type') == 'FunctionCall':
                return_type = self.check_function_call(args)
            else:
                return_type = self.infer_type(args)
        else:
            return_type = self.infer_type(args)
        
        if return_type and not self.check_type_compatibility(return_type, expected_return_type):
            self.add_error(f"Return type mismatch: expected '{expected_return_type}', got '{return_type}'")
    
    def check_statement(self, stmt, func_return_type):
        """Check a single statement"""
        if not isinstance(stmt, dict):
            return
        
        stmt_type = stmt.get('type')
        
        if stmt_type == 'declaration':
            self.check_declaration(stmt)
        
        elif stmt_type == 'OperatorExpression':
            self.check_operator_expression(stmt)
        
        elif stmt_type == 'FunctionCall':
            self.check_function_call(stmt)
        
        elif stmt_type == 'jump statement':
            keyword = stmt.get('keyword')
            if keyword == 'return':
                self.check_return_statement(stmt, func_return_type)
        
        elif stmt_type == 'Statements':
            self.enter_scope()
            for s in stmt.get('block', []):
                self.check_statement(s, func_return_type)
            self.exit_scope()
    
    def check_function(self, func_node):
        """Check function definition"""
        func_name = func_node.get('identifier')
        return_type = func_node.get('return type', 'void')
        params = func_node.get('params', [])
        body = func_node.get('body')
        
        # Extract parameters
        param_list = []
        for param in params:
            if isinstance(param, (list, tuple)) and len(param) >= 3:
                _, param_type, param_name = param
                param_list.append((param_name, param_type))
        
        # Declare function
        self.declare_function(func_name, return_type, param_list)
        
        # Enter function scope
        self.enter_scope()
        
        # Declare parameters as variables
        for param_name, param_type in param_list:
            self.declare_variable(param_name, param_type)
        
        # Check function body
        if body:
            self.check_statement(body, return_type)
        
        # Exit function scope
        self.exit_scope()
    
    def check(self, ast):
        """Main type checking entry point"""
        
        print("Starting Type Checking Phase")
        
        
        # First pass: collect all function declarations
        for node in ast:
            if isinstance(node, dict) and node.get('Function') == 'def':
                func_name = node.get('identifier')
                print(f"\nINFO: Checking function '{func_name}'")
                self.check_function(node)
        
        # Print results
        print("Type Checking Summary")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Variables declared: {len(self.symbol_table)}")
        print(f"Functions declared: {len(self.function_table)}")
        
        if self.errors:
            print("\nType checking failed with errors:\n")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\nType checking passed with warnings:\n")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\nType checking passed successfully!")
        
        # Save results to JSON
        results = {
            'success': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'symbol_table': {name: info['type'] for name, info in self.symbol_table.items()},
            'function_table': self.function_table
        }
        
        with open('type_check_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        #print("\nResults saved to type_check_results.json")


if __name__ == "__main__":
    # Read AST from file
    try:
        with open('ast.txt', 'r') as f:
            ast = json.load(f)
        
        # Create type checker and check
        checker = TypeChecker()
        checker.check(ast)
        
    except FileNotFoundError:
        print("ERROR: ast.txt not found!")
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse AST: {e}")


