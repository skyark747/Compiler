from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Import your ScopeAnalyzer & Symbol (from previous phase)
try:
    from scope_analysis import ScopeAnalyzer, Symbol
except Exception:
    # Minimal fallback symbol if import fails (for testing)
    @dataclass
    class Symbol:
        name: str
        kind: str
        datatype: Optional[str] = None
        info: Optional[dict] = None
        is_used: bool = False


#####
# Errors required by spec #
#####

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


@dataclass
class TypeErrorReport:
    kind: TypeChkError
    message: str
    node: Optional[Any] = None


##### TypeChecker #####
class TypeChecker:
    """
    TypeChecker that uses a previously-built symbol table (ScopeAnalyzer).
    It expects the AST format produced by your parser (dict nodes).
    """

    numeric_types = {"int", "float"}
    int_types = {"int"}
    bool_types = {"bool"}
    string_types = {"string"}
    primitive_types = numeric_types | bool_types | string_types | {"char", "void"}

    def __init__(self, ast: List[dict], scope_analyzer: Optional[ScopeAnalyzer] = None):
        self.ast = ast
        self.sa = scope_analyzer
        if self.sa is None:
            try:
                self.sa = ScopeAnalyzer()
                self.globals, self._sa_errors, self._sa_warnings = self.sa.analyze_program(ast)
            except Exception:
                self.globals = {}
        else:
            # find global scope table from scope_analyzer
            if hasattr(self.sa, "scopes") and len(self.sa.scopes) > 0:
                self.globals = self.sa.scopes[0]
            else:
                self.globals = {}
        # Errors collected
        self.errors: List[TypeErrorReport] = []

        # Local scope stack during type checking (list of dict name->Symbol)
        self.local_scopes: List[Dict[str, Symbol]] = []

        # Current function context
        self.current_fn_ret_type: Optional[str] = None
        self.current_fn_has_return: bool = False
        self.loop_depth = 0

    #####
    # Scope helpers (local view) #
    #####
    def push_scope(self):
        self.local_scopes.append({})

    def pop_scope(self):
        if self.local_scopes:
            self.local_scopes.pop()

    def declare_local(self, name: str, sym: Symbol):
        if not self.local_scopes:
            self.push_scope()
        self.local_scopes[-1][name] = sym

    def find_symbol(self, name: str) -> Optional[Symbol]:
        # local to global lookup
        for s in reversed(self.local_scopes):
            if name in s:
                return s[name]
        if isinstance(self.globals, dict) and name in self.globals:
            return self.globals[name]
        return None

    #####
    # Public entry #
    #####
    def type_check(self) -> List[TypeErrorReport]:
        # Walk top-level nodes
        for node in self.ast:
            if isinstance(node, dict) and node.get("Function") == "def":
                self._check_function(node)
            elif isinstance(node, dict) and "datatype" in node and "identifier" in node:
                # global var decl: check initializer
                self.push_scope()
                self._check_declaration(node, is_global=True)
                self.pop_scope()
            else:
                # other top-level constructs -- attempt to walk
                self._check_node(node)

        return self.errors

    #####
    # Node dispatch #
    #####
    def _check_node(self, node: Any) -> Optional[str]:
        """Return type of expression nodes; None for statements."""
        if node is None:
            return None

        if isinstance(node, list):
            t = None
            for n in node:
                t = self._check_node(n)
            return t

        if not isinstance(node, dict):
            # a raw token: literal or identifier
            if isinstance(node, str):
                return self._infer_type_from_token(node)
            return None

        # function definitions handled at top-level
        if node.get("Function") == "def":
            return None

        ntype = node.get("type")

        # Declarations
        if "datatype" in node and "identifier" in node:
            return self._check_declaration(node)

        if ntype == "Statements":
            return self._check_statements(node)

        if ntype == "OperatorExpression":
            return self._check_operator_expression(node)

        if ntype == "fn call":
            return self._check_function_call(node)

        if ntype == "jump statement":
            # return/break/continue/goto
            kw = node.get("keyword")
            if kw == "return":
                return self._check_return(node)
            if kw in ("break", "continue"):
                # scope analyzer already flags breaks outside loops; here we ensure break semantics if needed
                if self.loop_depth <= 0:
                    self._report(TypeChkError.ErroneousBreak,
                                 f"'{kw}' used outside of loop", node)
                return None
            # goto: no type checking
            return None

        if ntype == "conditional statement":
            # ensure condition is boolean
            cond = node.get("args")
            cond_type = self._check_node(cond)
            if cond_type is None:
                # empty or missing condition
                self._report(TypeChkError.EmptyExpression, "Empty condition in conditional statement", node)
            else:
                if not self._is_bool(cond_type):
                    self._report(TypeChkError.NonBooleanCondStmt,
                                 f"Condition expression must be boolean, got '{cond_type}'", node)
            # check body
            self.push_scope()
            self._check_node(node.get("body"))
            self.pop_scope()
            return None

        if ntype == "iteration":
            # typically for/while: args contain condition or init; treat args as cond when applicable
            self.loop_depth += 1
            args = node.get("args")
            if args is None:
                self._report(TypeChkError.EmptyExpression, "Empty condition in loop", node)
            else:
                cond_type = self._check_node(args)
                # if a conditional loop, ensure boolean condition
                if cond_type is not None and not self._is_bool(cond_type):
                    # some iteration forms (for(init;cond;step)) may produce None; only check if not None.
                    self._report(TypeChkError.ExpectedBooleanExpression,
                                 f"Loop condition must be boolean, got '{cond_type}'", node)
            # body
            self.push_scope()
            self._check_node(node.get("body"))
            self.pop_scope()
            self.loop_depth -= 1
            return None

        # label, postfix, scanning, other nodes: do a recursive walk
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                self._check_node(v)
            elif isinstance(v, str):
                # some raw tokens inside nodes should be type-checked as identifiers or literals
                pass
        return None

    #####
    # Declarations, statements #
    #####
    def _check_declaration(self, node: Dict, is_global: bool = False) -> Optional[str]:
        name = node.get("identifier")
        dtype = node.get("datatype")
        # initializer
        val = node.get("value")
        if val is None:
            # variable with no initializer is allowed; still declare
            sym = Symbol(name=name, kind="var", datatype=dtype, info={"node": node})
            if is_global:
                # global symbol table managed by scope analyzer
                pass
            else:
                self.declare_local(name, sym)
            return dtype

        # evaluate initializer type
        init_type = None
        if isinstance(val, dict):
            init_type = self._check_node(val)
        elif isinstance(val, str):
            init_type = self._infer_type_from_token(val)

        # declare symbol (after inferring initializer)
        sym = Symbol(name=name, kind="var", datatype=dtype, info={"node": node})
        if is_global:
            # globals are already in sa; but also keep local view for type checking if needed
            pass
        else:
            self.declare_local(name, sym)

        # check compatibility
        if init_type is None:
            # empty initializer (or unknown)
            self._report(TypeChkError.ErroneousVarDecl,
                         f"Initializer for '{name}' could not be resolved to a type", node)
        else:
            if not self._is_assignable(dtype, init_type):
                self._report(TypeChkError.ErroneousVarDecl,
                             f"Cannot initialize variable '{name}' of type '{dtype}' with value of type '{init_type}'", node)
        return dtype

    def _check_statements(self, node: Dict) -> None:
        self.push_scope()
        for stmt in node.get("block", []):
            self._check_node(stmt)
        self.pop_scope()
        return None

    #####
    # Operators and expressions #
    #####
    def _check_operator_expression(self, node: Dict) -> Optional[str]:
        """
        Expected node shape (as seen in parser):
        {"type":"OperatorExpression", "identifier": <left>, "op": "+", "value": <right>}
        If your AST uses different keys (e.g., "operator" instead of "op"), it will still try both.
        """
        left = node.get("identifier")
        right = node.get("value")
        op = node.get("op") or node.get("operator")

        # Empty expression checks
        if left is None or right is None or op is None:
            self._report(TypeChkError.EmptyExpression, "Operator expression missing operand/operator", node)
            return None

        ltype = None
        rtype = None

        # left
        if isinstance(left, dict):
            ltype = self._check_node(left)
        elif isinstance(left, str):
            ltype = self._infer_type_from_token(left)

        # right
        if isinstance(right, dict):
            rtype = self._check_node(right)
        elif isinstance(right, str):
            rtype = self._infer_type_from_token(right)

        # if either side unidentified, attempt lookup for identifier
        if ltype is None and isinstance(left, str):
            sym = self.find_symbol(left)
            if sym:
                ltype = sym.datatype
        if rtype is None and isinstance(right, str):
            sym = self.find_symbol(right)
            if sym:
                rtype = sym.datatype

        # boolean operators
        if op in ("&&", "||", "and", "or"):
            # both must be boolean
            if not self._is_bool(ltype) or not self._is_bool(rtype):
                self._report(TypeChkError.AttemptedBoolOpOnNonBools,
                             f"Boolean operator '{op}' requires boolean operands; got '{ltype}' and '{rtype}'", node)
            return "bool"

        # bitwise operators: &, |, ^  (we treat '^' as bitwise XOR)
        if op in ("&", "|", "^", "&=", "|=", "^="):
            # bitwise ops require integer operands (C allows integer types)
            if not self._is_int(ltype) or not self._is_int(rtype):
                self._report(TypeChkError.AttemptedBitOpOnNonNumeric,
                             f"Bitwise operator '{op}' requires integer operands; got '{ltype}' and '{rtype}'", node)
            return "int" if self._is_int(ltype) and self._is_int(rtype) else None

        # shift operators require integer operands and produce integer
        if op in ("<<", ">>", "<<=", ">>="):
            if not self._is_int(ltype) or not self._is_int(rtype):
                self._report(TypeChkError.AttemptedShiftOnNonInt,
                             f"Shift operator '{op}' requires integer operands; got '{ltype}' and '{rtype}'", node)
            return "int"

        # exponentiation (assume '**' operator if present)
        if op in ("**",):
            if not self._is_numeric(ltype) or not self._is_numeric(rtype):
                self._report(TypeChkError.AttemptedExponentiationOfNonNumeric,
                             f"Exponentiation '{op}' requires numeric operands; got '{ltype}' and '{rtype}'", node)
            # float if either is float, else int
            return "float" if (ltype == "float" or rtype == "float") else "int"

        # addition / subtraction / multiplication / division / modulus
        if op in ("+", "-", "*", "/", "%"):
            # For '+', some languages allow string concat; your spec requires AttemptedAddOpOnNonNumeric
            if not self._is_numeric(ltype) or not self._is_numeric(rtype):
                self._report(TypeChkError.AttemptedAddOpOnNonNumeric,
                             f"Arithmetic operator '{op}' requires numeric operands; got '{ltype}' and '{rtype}'", node)
                return None
            # promotion
            if ltype == "float" or rtype == "float":
                return "float"
            return "int"

        # relational operators -> boolean result, operands must be comparable
        if op in ("==", "!=", "<", "<=", ">", ">="):
            # allow comparisons of same primitive type (or numeric-to-numeric)
            if ltype is None or rtype is None:
                self._report(TypeChkError.ExpressionTypeMismatch,
                             f"Comparison '{op}' with unknown operand types '{ltype}' and '{rtype}'", node)
                return "bool"
            if self._is_numeric(ltype) and self._is_numeric(rtype):
                return "bool"
            if ltype == rtype:
                return "bool"
            # else mismatch
            self._report(TypeChkError.ExpressionTypeMismatch,
                         f"Comparison '{op}' between incompatible types '{ltype}' and '{rtype}'", node)
            return "bool"

        # if operator assignment forms like '+=', '-=' -> check right assignable to left type
        if op.endswith("=") and len(op) >= 2:
            # e.g., "+=", "&=", handle as binary op then assign
            base_op = op[:-1]
            # we treat this conservatively: require types compatible with base op semantics
            # reuse a simulated binary check by building a fake node
            fake = {"type": "OperatorExpression", "identifier": left, "op": base_op, "value": right}
            result_type = self._check_operator_expression(fake)
            # now check assignability to left
            if not self._is_assignable(ltype, result_type):
                self._report(TypeChkError.ExpressionTypeMismatch,
                             f"Compound assignment '{op}' results in '{result_type}' which cannot be assigned to '{ltype}'", node)
            return ltype

        # unknown operator: we try to be conservative and return None but warn
        self._report(TypeChkError.ExpressionTypeMismatch,
                     f"Unknown or unhandled operator '{op}'", node)
        return None

    #####
    # Function calls #
    #####
    def _check_function_call(self, node: Dict) -> Optional[str]:
        # node['args'] expected to be [("identifier", "fname"), arg1, arg2, ...] per your parser
        args = node.get("args", [])
        if not args:
            self._report(TypeChkError.EmptyExpression, "Empty function call", node)
            return None

        # extract function name & actual args
        first = args[0]
        if isinstance(first, tuple) and first[0] == "identifier":
            fname = first[1]
            actual_args = args[1:]
        elif isinstance(first, str):
            fname = first
            actual_args = args[1:]
        else:
            # indirect call / complex form: skip precise checking
            fname = None
            actual_args = args

        # check existence
        if fname:
            f_sym = self.find_symbol(fname)
            if not f_sym or f_sym.kind != "func":
                self._report(TypeChkError.ExpressionTypeMismatch,
                             f"Call to undefined function '{fname}'", node)
                return None
            # get declared params
            fn_node = f_sym.info.get("node") if f_sym.info else None
            declared = []
            if fn_node:
                for p in fn_node.get("params", []):
                    if isinstance(p, (list, tuple)) and p[0] == "Param":
                        declared.append(p[1])

            # check param count
            if len(actual_args) != len(declared):
                self._report(TypeChkError.FnCallParamCount,
                             f"Function '{fname}' expects {len(declared)} args but got {len(actual_args)}", node)
            # check param types where possible
            for i, a in enumerate(actual_args):
                atype = None
                if isinstance(a, dict):
                    atype = self._check_node(a)
                elif isinstance(a, tuple) and a[0] == "identifier":
                    sym = self.find_symbol(a[1])
                    atype = sym.datatype if sym else None
                elif isinstance(a, str):
                    atype = self._infer_type_from_token(a)
                    if atype is None:
                        # maybe identifier string
                        sym = self.find_symbol(a)
                        atype = sym.datatype if sym else None

                if i < len(declared):
                    expected = declared[i]
                    if atype is None:
                        # unknown arg type is treated as error for param type mismatch
                        self._report(TypeChkError.FnCallParamType,
                                     f"In call to '{fname}', argument {i+1} has unknown type; expected '{expected}'", node)
                    else:
                        if not self._is_assignable(expected, atype):
                            self._report(TypeChkError.FnCallParamType,
                                         f"In call to '{fname}', argument {i+1} expected '{expected}', got '{atype}'", node)
            # return type
            ret = fn_node.get("return type") if fn_node else None
            return ret
        else:
            # could be function pointer call or member call; skip
            return None

    #####
    # Return #
    #####
    def _check_return(self, node: Dict) -> Optional[str]:
        expr = node.get("args")
        self.current_fn_has_return = True
        if expr is None:
            # returning nothing
            if self.current_fn_ret_type and self.current_fn_ret_type != "void":
                self._report(TypeChkError.ErroneousReturnType,
                             f"Function expects return type '{self.current_fn_ret_type}' but return has no value", node)
            return None
        # type of expression
        if isinstance(expr, dict):
            t = self._check_node(expr)
        elif isinstance(expr, str):
            t = self._infer_type_from_token(expr)
            if t is None:
                sym = self.find_symbol(expr)
                t = sym.datatype if sym else None
        else:
            t = None

        if self.current_fn_ret_type is None:
            # No declared return type: treat as error? we'll warn with ErroneousReturnType
            if t is not None:
                pass
            return t

        if t is None:
            self._report(TypeChkError.ErroneousReturnType,
                         f"Return expression type could not be determined for function expecting '{self.current_fn_ret_type}'", node)
            return None

        if not self._is_assignable(self.current_fn_ret_type, t):
            self._report(TypeChkError.ErroneousReturnType,
                         f"Return type mismatch: function expects '{self.current_fn_ret_type}', got '{t}'", node)
        return t

    #####
    # Utilities: types & reporting #
    #####
    def _is_numeric(self, t: Optional[str]) -> bool:
        return t in self.numeric_types

    def _is_int(self, t: Optional[str]) -> bool:
        return t in self.int_types

    def _is_bool(self, t: Optional[str]) -> bool:
        return t in self.bool_types

    def _is_assignable(self, to_type: Optional[str], from_type: Optional[str]) -> bool:
        if to_type is None or from_type is None:
            return False
        if to_type == from_type:
            return True
        # allow int -> float promotion
        if to_type == "float" and from_type == "int":
            return True
        return False

    def _infer_type_from_token(self, tok: str) -> Optional[str]:
        if tok is None:
            return None
        s = tok.strip()
        if s == '':
            return None
        if s.startswith('"') and s.endswith('"'):
            return "string"
        if s.startswith("'") and s.endswith("'"):
            return "char"
        if s in ("true", "false"):
            return "bool"
        # numeric detection
        try:
            if "." in s:
                float(s)
                return "float"
            else:
                int(s)
                return "int"
        except Exception:
            # if identifier, try symbol table lookup
            sym = self.find_symbol(s)
            return sym.datatype if sym else None

    def _report(self, kind: TypeChkError, message: str, node: Optional[Any] = None):
        self.errors.append(TypeErrorReport(kind, message, node))

    #####
    # Helper for function-checking wrapper #
    #####
    def _check_function(self, fn_node: Dict):
        
        self.current_fn_ret_type = fn_node.get("return type") or fn_node.get("rtype") or None
        self.current_fn_has_return = False
        self.push_scope()

        for p in fn_node.get("params", []):
            if isinstance(p, (list, tuple)) and p[0] == "Param":
                _, ptype, pname = p
                if pname:
                    self.declare_local(pname, Symbol(name=pname, kind="param", datatype=ptype, info={"node": fn_node}))

        self._check_node(fn_node.get("body"))

        if self.current_fn_ret_type and self.current_fn_ret_type != "void" and not self.current_fn_has_return:
            self._report(TypeChkError.ReturnStmtNotFound,
                         f"Function '{fn_node.get('identifier')}' of type '{self.current_fn_ret_type}' has no return statement", fn_node)

        self.pop_scope()
        self.current_fn_ret_type = None
        self.current_fn_has_return = False
