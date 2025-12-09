from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Set

class TypeChkError(Enum):
    ErroneousVarDecl = auto()
    FnCallParamCount = auto()
    FnCallParamType = auto()
    ErroneousReturnType = auto()
    ExpressionTypeMismatch = auto()
    ExpectedBooleanExpression = auto()
    ErroneousBreak = auto()
    NonBooleanCondStmt = auto()
    EmptyExpression = auto()
    AttemptedBoolOpOnNonBools = auto()
    AttemptedBitOpOnNonNumeric = auto()
    AttemptedShiftOnNonInt = auto()
    AttemptedAddOpOnNonNumeric = auto()
    AttemptedExponentiationOfNonNumeric = auto()
    ReturnStmtNotFound = auto()
    UnknownIdentifier = auto()
    AssignmentTypeMismatch = auto()
    FunctionRedefinition = auto()
    TooManyReturnValues = auto()
    MissingReturnValue = auto()
    ArityMismatch = auto()
    MalformedExpression = auto()


PRIMITIVE_TYPES = {'int', 'float', 'bool', 'string', 'void'}  # void for functions that return nothing

def is_numeric(t: str) -> bool:
    return t in ('int', 'float')

def numeric_result_type(a: str, b: str) -> str:
    # if either is float -> float else int
    if a == 'float' or b == 'float':
        return 'float'
    return 'int'

##### TypeChecker #####

class TypeChecker:
    """
    TypeChecker operates over:
      - symbol_table: list-of-dicts representing nested scopes (outermost first).
        Each dict maps name->Symbol-like objects (must have .name, .kind, .datatype, .is_used (optional))
      - program_ast: list of top-level nodes (function defs, global decls, etc.)
    """

    def __init__(self, symbol_table: List[Dict[str, Any]], program_ast: List[dict], builtins: Optional[Dict[str, Tuple[List[str], str]]] = None):
        self.symbol_table = symbol_table  # e.g., self.scopes from your analyzer; list from outermost -> innermost
        self.program_ast = program_ast
        self.errors: List[Tuple[TypeChkError, str, Optional[Any]]] = []
        self.warnings: List[Tuple[str, str, Optional[Any]]] = []
        # builtins: mapping name -> (param_types_list, return_type)
        self.builtins = builtins or {
            'print': (['string'], 'void'),
            'input': ([], 'string'),
        }

        # runtime state when entering functions / loops
        self.loop_depth = 0
        self.in_function = False
        self.current_function_return: Optional[str] = None
        self.current_function_has_return: bool = False

##### Public entry #####

    def run(self) -> Tuple[List[Tuple[TypeChkError, str, Optional[Any]]], List[Tuple[str, str, Optional[Any]]]]:
        # Walk top-level: register/check functions' bodies
        for node in self.program_ast:
            self._walk_node(node, self.symbol_table)
        # For each function symbol in global scope, ensure non-void declares have returns
        # (some languages require at least one return - included as a check)
        # We already track returns while visiting function bodies.
        return self.errors, self.warnings

##### Utils for symbol lookup #####

    def find_symbol(self, name: str) -> Optional[Any]:
        # symbol_table is list-of-dicts outer->inner
        for scope in reversed(self.symbol_table):
            if name in scope:
                return scope[name]
        return None

    def add_error(self, code: TypeChkError, msg: str, node: Optional[Any] = None):
        self.errors.append((code, msg, node))

    def add_warning(self, kind: str, msg: str, node: Optional[Any] = None):
        self.warnings.append((kind, msg, node))


##### Node walkers #####

    def _walk_node(self, node: Any, symbol_table: List[Dict[str, Any]]):
        if node is None:
            return

        # nodes may be lists
        if isinstance(node, list):
            for n in node:
                self._walk_node(n, symbol_table)
            return

        if not isinstance(node, dict):
            return

        # Detect function definition nodes (matching your scope analyzer style)
        if node.get("Function") == "def":
            self._walk_function_def(node, symbol_table)
            return

        ntype = node.get('type')

        if ntype == 'Statements':
            self._walk_statements(node, symbol_table)
            return

        if 'datatype' in node and 'identifier' in node:
            # variable declaration
            self._walk_declaration(node, symbol_table)
            return

        if ntype == 'assignment':
            self._walk_assignment(node, symbol_table)
            return

        if ntype == 'conditional statement':
            self._walk_conditional(node, symbol_table)
            return

        if ntype == 'iteration':
            self._walk_iteration(node, symbol_table)
            return

        if ntype == 'jump statement':
            self._walk_jump(node, symbol_table)
            return

        if ntype in ('OperatorExpression', 'PostfixExpression', 'ScanningExpression'):
            # possibly expression node; try infer
            _ = self._infer_expr_type(node)
            return

        if ntype == 'label':
            return

        if ntype == 'fn call':
            # in some ASTs fn call nodes are simple dicts; else the expression parser nodes will be handled by _infer_expr_type
            self._walk_function_call_node(node, symbol_table)
            return

        # fallback: recurse over values
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                self._walk_node(v, symbol_table)

##### Specific walkers #####

    def _walk_function_def(self, node: dict, symbol_table: List[Dict[str, Any]]):
        # Expect node keys: identifier, params, return type, body
        fname = node.get('identifier')
        declared_ret = node.get('return type') or 'void'
        params = node.get('params', [])

        # enter function
        prev_in_function = self.in_function
        prev_ret_type = self.current_function_return
        prev_has_return = self.current_function_has_return

        self.in_function = True
        self.current_function_return = declared_ret
        self.current_function_has_return = False

        # Create a new scope for parameters and body type-checking.
        # We expect symbol_table to be a list-of-dicts; append a new dict for this function's scope,
        # but we should make a shallow copy so lookups above continue to work.
        func_scope = {}
        # Parameters come in as tuples: ('Param', type, name) according to your analyzer
        for p in params:
            if isinstance(p, (list, tuple)) and len(p) >= 3 and p[0] == 'Param':
                _, ptype, pname = p
                if not pname:
                    continue
                # record parameter in func_scope
                func_scope[pname] = SimpleSym(pname, 'param', ptype, info={'node': node})
            else:
                # if not in that shape, skip
                pass

        # push func scope to symbol_table
        symbol_table.append(func_scope)

        # walk body
        self._walk_node(node.get('body'), symbol_table)

        # after walking body, ensure return existence for non-void
        if self.current_function_return != 'void' and not self.current_function_has_return:
            # add an error that required return was not found
            self.add_error(TypeChkError.ReturnStmtNotFound,
                           f"Function '{fname}' declared to return '{self.current_function_return}' but no return found", node)

        # pop func scope
        symbol_table.pop()

        # restore
        self.in_function = prev_in_function
        self.current_function_return = prev_ret_type
        self.current_function_has_return = prev_has_return

    def _walk_statements(self, node: dict, symbol_table: List[Dict[str, Any]]):
        # statements node has 'block': list
        block = node.get('block', [])
        # push a new local scope for the block (if your prior phase used that, adjust accordingly)
        block_scope = {}
        symbol_table.append(block_scope)
        for s in block:
            self._walk_node(s, symbol_table)
        symbol_table.pop()

    def _walk_declaration(self, node: dict, symbol_table: List[Dict[str, Any]]):
        name = node.get('identifier')
        dtype = node.get('datatype')
        if dtype is None:
            self.add_error(TypeChkError.ErroneousVarDecl, f"Variable '{name}' declared without type", node)
            return
        # check initializer compatibility
        val = node.get('value')
        if val is not None:
            if isinstance(val, dict):
                val_type = self._infer_expr_type(val)
            elif isinstance(val, str):
                # if it's a raw string expression we attempt to parse using the expression parser shape
                # but we cannot rely on that; simple heuristic: literals are quoted or numeric
                if val.startswith('"') and val.endswith('"'):
                    val_type = 'string'
                else:
                    # unknown string expression: we conservatively try to find identifier types
                    val_type = None
            else:
                val_type = None

            if val_type is None:
                # can't determine type but if initializer is string literal or number or an identifier, handle it:
                if isinstance(val, str):
                    if val.startswith('"') and val.endswith('"'):
                        val_type = 'string'
                    elif val.isdigit():
                        val_type = 'int'
                    else:
                        # maybe an identifier - look it up
                        sym = self.find_symbol(val)
                        if sym and getattr(sym, 'datatype', None):
                            val_type = sym.datatype
                        else:
                            val_type = None

            if val_type is not None:
                if not self._is_assign_compatible(dtype, val_type):
                    self.add_error(TypeChkError.AssignmentTypeMismatch,
                                   f"Initializer type '{val_type}' not compatible with declared type '{dtype}' for variable '{name}'", node)

        # add variable to current scope
        cur_scope = symbol_table[-1]
        cur_scope[name] = SimpleSym(name, 'var', dtype, info={'node': node})

    def _walk_assignment(self, node: dict, symbol_table: List[Dict[str, Any]]):
        # expected shape: {type:'assignment', target: {type:'Identifier', name:...} or string, value: expression}
        target = node.get('target')
        value = node.get('value')
        # find target type
        if isinstance(target, dict) and target.get('type') == 'Identifier':
            tname = target.get('name')
            sym = self.find_symbol(tname)
            if not sym:
                self.add_error(TypeChkError.UnknownIdentifier, f"Assignment target '{tname}' not declared", node)
                return
            ttype = getattr(sym, 'datatype', None)
        elif isinstance(target, str):
            sym = self.find_symbol(target)
            if not sym:
                self.add_error(TypeChkError.UnknownIdentifier, f"Assignment target '{target}' not found", node)
                return
            ttype = getattr(sym, 'datatype', None)
        else:
            self.add_error(TypeChkError.ExpressionTypeMismatch, "Unsupported assignment target shape", node)
            return

        vtype = None
        if isinstance(value, dict):
            vtype = self._infer_expr_type(value)
        elif isinstance(value, str):
            if value.startswith('"') and value.endswith('"'):
                vtype = 'string'
            elif value.isdigit():
                vtype = 'int'
            else:
                symv = self.find_symbol(value)
                if symv:
                    vtype = getattr(symv, 'datatype', None)
        else:
            vtype = None

        if vtype is None:
            # could not determine assignment type; flag malformed
            self.add_error(TypeChkError.MalformedExpression, f"Could not determine assignment value type for '{target}'", node)
            return

        if not self._is_assign_compatible(ttype, vtype):
            self.add_error(TypeChkError.AssignmentTypeMismatch,
                           f"Cannot assign value of type '{vtype}' to target of type '{ttype}'", node)

    def _walk_conditional(self, node: dict, symbol_table: List[Dict[str, Any]]):
        args = node.get('args')  # expression
        cond_type = None
        if args:
            cond_type = self._infer_expr_type(args)
        if cond_type is None:
            self.add_error(TypeChkError.EmptyExpression, "Empty condition expression", node)
            cond_type = 'void'
        if cond_type != 'bool':
            self.add_error(TypeChkError.NonBooleanCondStmt, f"Expected boolean condition, got '{cond_type}'", node)

        # body check
        self._walk_node(node.get('body'), symbol_table)

    def _walk_iteration(self, node: dict, symbol_table: List[Dict[str, Any]]):
        # increment loop depth
        self.loop_depth += 1
        args = node.get('args')
        if args:
            cond_type = self._infer_expr_type(args)
            if cond_type is None:
                self.add_error(TypeChkError.EmptyExpression, "Empty iteration condition", node)
            elif cond_type != 'bool':
                self.add_error(TypeChkError.ExpectedBooleanExpression, f"Loop condition must be boolean, got '{cond_type}'", node)

        # body
        self._walk_node(node.get('body'), symbol_table)
        self.loop_depth -= 1

    def _walk_jump(self, node: dict, symbol_table: List[Dict[str, Any]]):
        kw = node.get('keyword')
        if kw == 'return':
            # handle optional return value
            val = node.get('args')
            rtype = 'void'
            if val is not None:
                if isinstance(val, dict):
                    rtype = self._infer_expr_type(val)
                elif isinstance(val, str):
                    if val.startswith('"') and val.endswith('"'):
                        rtype = 'string'
                    elif val.isdigit():
                        rtype = 'int'
                    else:
                        sym = self.find_symbol(val)
                        rtype = getattr(sym, 'datatype', None) if sym else None

            # check against current function return type
            if not self.in_function or self.current_function_return is None:
                # return outside function — scope analyzer may already catch this — we still flag
                self.add_error(TypeChkError.ErroneousReturnType, "Return statement outside function or unknown expected return type", node)
            else:
                expected = self.current_function_return
                if rtype is None:
                    # unknown return expression type
                    self.add_error(TypeChkError.ErroneousReturnType, f"Unable to determine return expression type, expected '{expected}'", node)
                else:
                    if not self._is_assign_compatible(expected, rtype):
                        self.add_error(TypeChkError.ErroneousReturnType, f"Return type '{rtype}' not compatible with function return '{expected}'", node)
                    else:
                        self.current_function_has_return = True

        elif kw in ('break', 'continue'):
            if self.loop_depth == 0:
                self.add_error(TypeChkError.ErroneousBreak, f"'{kw}' used outside loop", node)
        elif kw == 'goto':
            # labels not type-checked here
            pass

    def _walk_function_call_node(self, node: dict, symbol_table: List[Dict[str, Any]]):
        # shape: {type:'fn call', args: [..] } where args[0] might be function identifier in some ASTs
        # We try to resolve function name and types
        args = node.get('args', [])
        if not args:
            return
        # heuristics: if first arg is tuple ('identifier','fname') or is string name, etc.
        fname = None
        arg_exprs = []
        if args and isinstance(args[0], tuple) and args[0][0] == 'identifier':
            fname = args[0][1]
            arg_exprs = args[1:]
        elif args and isinstance(args[0], str):
            fname = args[0]
            arg_exprs = args[1:]
        else:
            # other shape — abort
            return

        # find function symbol
        fn_sym = self.find_symbol(fname)
        if not fn_sym and fname not in self.builtins:
            self.add_error(TypeChkError.UnknownIdentifier, f"Function '{fname}' not declared", node)
            return

        declared_param_types = []
        declared_ret = 'void'
        # if builtin
        if fname in self.builtins:
            declared_param_types, declared_ret = self.builtins[fname]
        else:
            declared_ret = getattr(fn_sym, 'datatype', None)
            # for functions, we may store parameter info in sym.info or elsewhere; attempt to retrieve
            info = getattr(fn_sym, 'info', None)
            if info and isinstance(info, dict):
                # many analyzers store param list under 'node' or so
                n = info.get('node')
                if n:
                    params = n.get('params', [])
                    for p in params:
                        if isinstance(p, (list,tuple)) and p[0] == 'Param':
                            _, ptype, pname = p
                            declared_param_types.append(ptype)

        # evaluate actual arg types
        actual_types = []
        for a in arg_exprs:
            if isinstance(a, dict):
                actual_types.append(self._infer_expr_type(a))
            elif isinstance(a, str):
                if a.startswith('"') and a.endswith('"'):
                    actual_types.append('string')
                elif a.isdigit():
                    actual_types.append('int')
                else:
                    sym = self.find_symbol(a)
                    actual_types.append(getattr(sym, 'datatype', None) if sym else None)
            elif isinstance(a, tuple) and a[0] == 'identifier':
                sym = self.find_symbol(a[1])
                actual_types.append(getattr(sym, 'datatype', None) if sym else None)
            else:
                actual_types.append(None)

        # param count check
        if declared_param_types and len(actual_types) != len(declared_param_types):
            self.add_error(TypeChkError.FnCallParamCount,
                           f"Function '{fname}' expects {len(declared_param_types)} args but {len(actual_types)} were given", node)
            return

        # param type check
        for i, (act, exp) in enumerate(zip(actual_types, declared_param_types)):
            if act is None:
                self.add_error(TypeChkError.FnCallParamType,
                               f"Could not determine type of argument {i} in call to '{fname}' (expected '{exp}')", node)
            else:
                if not self._is_assign_compatible(exp, act):
                    self.add_error(TypeChkError.FnCallParamType,
                                   f"Argument {i} to '{fname}' has type '{act}' but expected '{exp}'", node)

        # return type not used here; callers may already check
        return declared_ret


##### Expression inference #####


    def _infer_expr_type(self, expr: Any) -> Optional[str]:
        """
        Return one of 'int','float','bool','string' or None if unknown/malformed.
        Accepts expressions in either:
          - the simple dict shapes from your shunting-yard: BinaryOp, UnaryOp, FnCall, Identifier, Literal
          - or some other shapes: tuple identifier, etc.
        """
        if expr is None:
            return None
        if isinstance(expr, str):
            # literal heuristics
            if expr.startswith('"') and expr.endswith('"'):
                return 'string'
            if expr.isdigit():
                return 'int'
            # lookup identifier
            sym = self.find_symbol(expr)
            return getattr(sym, 'datatype', None) if sym else None

        if not isinstance(expr, dict):
            return None

        etype = expr.get('type')

        if etype == 'Literal':
            return expr.get('literal_type') or self._literal_infer(expr.get('value'))

        if etype == 'Identifier':
            name = expr.get('name')
            sym = self.find_symbol(name)
            if not sym:
                self.add_error(TypeChkError.UnknownIdentifier, f"Identifier '{name}' used but not declared", expr)
                return None
            return getattr(sym, 'datatype', None)

        if etype == 'FnCall':
            # function call shaped node created by shunting-yard
            fname = expr.get('name')
            args = expr.get('args', [])
            # reuse fn call checker
            # build a fake node resembling 'fn call' with args [fname, ...] for compatibility
            fake = {'type':'fn call', 'args': [fname] + args}
            return self._walk_function_call_node(fake, self.symbol_table) or 'void'

        if etype == 'UnaryOp':
            op = expr.get('op')
            operand = expr.get('operand')
            ot = self._infer_expr_type(operand)
            if ot is None:
                self.add_error(TypeChkError.ExpressionTypeMismatch, f"Unary operand type unknown for op '{op}'", expr)
                return None
            # unary plus/minus -> numeric
            if op in ('u+', 'u-', '+', '-'):
                if not is_numeric(ot):
                    self.add_error(TypeChkError.ExpressionTypeMismatch, f"Unary '{op}' applied to non-numeric '{ot}'", expr)
                    return None
                return ot
            if op == '!':
                if ot != 'bool':
                    self.add_error(TypeChkError.AttemptedBoolOpOnNonBools, f"'!' applied to non-bool '{ot}'", expr)
                    return None
                return 'bool'
            # fallback
            return ot

        if etype == 'BinaryOp':
            op = expr.get('op')
            left = expr.get('left')
            right = expr.get('right')
            lt = self._infer_expr_type(left)
            rt = self._infer_expr_type(right)

            if lt is None or rt is None:
                # propagate unknown type but report
                self.add_error(TypeChkError.ExpressionTypeMismatch, f"Cannot determine operand types for '{op}' (left:{lt}, right:{rt})", expr)
                return None

            # boolean operators
            if op in ('&&', '||'):
                if lt != 'bool' or rt != 'bool':
                    self.add_error(TypeChkError.AttemptedBoolOpOnNonBools, f"Boolean op '{op}' applied to non-bools ('{lt}','{rt}')", expr)
                    return None
                return 'bool'

            # equality
            if op in ('==','!='):
                # allow equality between same types
                if lt != rt:
                    # special-case numeric cross-type equality (int vs float allowed)
                    if is_numeric(lt) and is_numeric(rt):
                        return 'bool'
                    self.add_error(TypeChkError.ExpressionTypeMismatch, f"Equality '{op}' between incompatible types '{lt}' and '{rt}'", expr)
                    return None
                return 'bool'

            # comparisons < <= > >=
            if op in ('<','<=','>','>='):
                if not (is_numeric(lt) and is_numeric(rt)):
                    self.add_error(TypeChkError.ExpressionTypeMismatch, f"Comparison '{op}' requires numeric operands (got '{lt}','{rt}')", expr)
                    return None
                return 'bool'

            # bitwise ops: &, |, ^  (require integer operands)
            if op in ('&','|','^'):
                if lt not in ('int',) or rt not in ('int',):
                    self.add_error(TypeChkError.AttemptedBitOpOnNonNumeric, f"Bitwise op '{op}' requires integer operands (got '{lt}','{rt}')", expr)
                    return None
                return 'int'

            # shifts << >>
            if op in ('<<','>>'):
                if lt != 'int' or rt != 'int':
                    self.add_error(TypeChkError.AttemptedShiftOnNonInt, f"Shift '{op}' requires integer operands (got '{lt}','{rt}')", expr)
                    return None
                return 'int'

            # additive + - (note: '+' on strings could mean concatenation)
            if op in ('+','-'):
                if op == '+' and lt == 'string' and rt == 'string':
                    return 'string'
                if not (is_numeric(lt) and is_numeric(rt)):
                    self.add_error(TypeChkError.AttemptedAddOpOnNonNumeric, f"Add/Sub '{op}' requires numeric operands (got '{lt}','{rt}')", expr)
                    return None
                return numeric_result_type(lt, rt)

            # multiplicative * / %
            if op in ('*','/','%'):
                if not (is_numeric(lt) and is_numeric(rt)):
                    self.add_error(TypeChkError.AttemptedAddOpOnNonNumeric, f"Mul/Div/Mod '{op}' requires numeric operands (got '{lt}','{rt}')", expr)
                    return None
                return numeric_result_type(lt, rt)

            # exponentiation **
            if op == '**':
                if not (is_numeric(lt) and is_numeric(rt)):
                    self.add_error(TypeChkError.AttemptedExponentiationOfNonNumeric, f"Exponentiation requires numeric operands (got '{lt}','{rt}')", expr)
                    return None
                # exponentiation with floats -> float
                return numeric_result_type(lt, rt)

            # assignment-like ops (+= etc.) - we treat them as binary with compatibility rules
            if op in ('=','+=','-=','*=','/='):
                # left must be a modifiable lvalue - our AST likely supplies actual identifier nodes
                # check compatibility: assigning rt into lt
                if op == '=':
                    if not self._is_assign_compatible(lt, rt):
                        self.add_error(TypeChkError.AssignmentTypeMismatch, f"Assignment: cannot assign '{rt}' to '{lt}'", expr)
                        return None
                    return lt
                else:
                    # compound: x += y -> requires numeric (or for += maybe string+string)
                    if op == '+=' and lt == 'string' and rt == 'string':
                        return 'string'
                    if not (is_numeric(lt) and is_numeric(rt)):
                        self.add_error(TypeChkError.AttemptedAddOpOnNonNumeric, f"Compound assignment '{op}' requires numeric operands (got '{lt}','{rt}')", expr)
                        return None
                    return numeric_result_type(lt, rt)

            # fallback unknown operator
            self.add_error(TypeChkError.MalformedExpression, f"Unknown operator '{op}'", expr)
            return None

        # If expression shape is something else, attempt to find a nested expression
        # or treat as malformed
        # e.g., your earlier analyzer sometimes leaves expression fragments as dict with keys being fields
        # try to search for known expression keys
        for candidate in ('expr','value','args','lhs','rhs'):
            if candidate in expr:
                return self._infer_expr_type(expr[candidate])

        return None

    def _literal_infer(self, v: Any) -> Optional[str]:
        if isinstance(v, str):
            return 'string'
        if isinstance(v, bool):
            return 'bool'
        if isinstance(v, int):
            return 'int'
        if isinstance(v, float):
            return 'float'
        return None


##### Type utilities #####


    def _is_assign_compatible(self, target: Optional[str], src: Optional[str]) -> bool:
        """
        Check if a value of type `src` can be assigned to a location of type `target`.
        Allows numeric widening: int -> float is allowed; float->int is not.
        """
        if target is None or src is None:
            return False
        if target == src:
            return True
        if target == 'float' and src == 'int':
            return True
        # allow assignment of anything to 'string' only if src is string (no implicit casts)
        return False


##### Simple symbol shim used by this checker if symbols are plain dicts/objects #####


class SimpleSym:
    def __init__(self, name: str, kind: str, datatype: Optional[str], info: Optional[dict] = None):
        self.name = name
        self.kind = kind
        self.datatype = datatype
        self.info = info or {}
        self.is_used = False



##### Example usage & simple test harness #####


if __name__ == '__main__':
    # tiny fake symbol table to illustrate usage: [global_scope, ...]
    global_scope = {}
    # pretend we have a function 'foo' declared returning int and params (int x, float y)
    foo_node = {'Function':'def', 'identifier':'foo', 'params':[('Param','int','x'), ('Param','float','y')], 'return type':'int', 'body': {'type':'Statements', 'block': [
        {'type':'jump statement', 'keyword':'return', 'args': {'type':'Literal', 'value':'0', 'literal_type':'int'}}
    ]}}
    # register foo symbol in global scope
    global_scope['foo'] = SimpleSym('foo','func','int', info={'node': foo_node})

    # add some variables
    global_scope['a'] = SimpleSym('a','var','int')
    global_scope['b'] = SimpleSym('b','var','float')
    global_scope['s'] = SimpleSym('s','var','string')

    symbol_table = [global_scope]

    # program AST sample: call foo with bad arg types etc.
    program = [
        foo_node,
        # statements: call foo('bad', 2.0)
        {'type':'Statements', 'block': [
            {'type':'fn call', 'args': [('identifier','foo'), {'type':'Literal','value':'"hello"','literal_type':'string'}, {'type':'Literal','value':'2.0','literal_type':'float'}]},
            # assignment: a = s  (int = string)
            {'type':'assignment', 'target': {'type':'Identifier','name':'a'}, 'value': {'type':'Identifier','name':'s'}},
            # conditional with non-bool
            {'type':'conditional statement', 'args': {'type':'Identifier','name':'a'}, 'body': {'type':'Statements','block':[]}},
        ]}
    ]

    tc = TypeChecker(symbol_table, program)
    errors, warnings = tc.run()
    print("Errors:")
    for e in errors:
        print(e)
    print("Warnings:")
    for w in warnings:
        print(w)
