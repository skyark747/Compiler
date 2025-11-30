# type_checker.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# try to import Symbol from scope analyzer, fallback to minimal
try:
    from scope_analysis import Symbol, ScopeAnalyzer
except Exception:
    @dataclass
    class Symbol:
        name: str
        kind: str
        datatype: Optional[str] = None
        info: Optional[dict] = None
        is_used: bool = False
    ScopeAnalyzer = None

# ---------- Errors enum ----------
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

# ---------- TypeChecker ----------
class TypeChecker:
    numeric = {"int", "float"}
    int_only = {"int"}
    bools = {"bool"}
    strings = {"string"}
    primitives = numeric | bools | strings | {"char", "void"}

    def __init__(self, ast: List[dict], scope_analyzer: Optional["ScopeAnalyzer"] = None):
        self.ast = ast
        self.sa = scope_analyzer
        if self.sa is None:
            try:
                self.sa = ScopeAnalyzer()
                self.globals, _, _ = self.sa.analyze_program(ast)
            except Exception:
                self.globals = {}
        else:
            self.globals = self.sa.scopes[0] if hasattr(self.sa, "scopes") and self.sa.scopes else {}

        self.errors: List[TypeErrorReport] = []
        self.local_scopes: List[Dict[str, Symbol]] = []
        self.current_fn_ret: Optional[str] = None
        self.current_fn_has_return: bool = False
        self.loop_depth = 0

    # ---------- scope helpers ----------
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
        for s in reversed(self.local_scopes):
            if name in s:
                return s[name]
        if isinstance(self.globals, dict) and name in self.globals:
            return self.globals[name]
        return None

    # ---------- public ----------
    def type_check(self) -> List[TypeErrorReport]:
        for node in self.ast:
            if isinstance(node, dict) and node.get("Function") == "def":
                self._check_function(node)
            elif isinstance(node, dict) and "datatype" in node and "identifier" in node:
                # top-level var decl
                self.push_scope()
                self._check_declaration(node, is_global=True)
                self.pop_scope()
            else:
                self._check_node(node)
        return self.errors

    # ---------- node dispatch ----------
    def _check_node(self, node: Any) -> Optional[str]:
        if node is None:
            return None
        if isinstance(node, list):
            t = None
            for n in node:
                t = self._check_node(n)
            return t
        if not isinstance(node, dict):
            # raw token: identifier or literal
            if isinstance(node, str):
                return self._infer_type_from_token(node)
            return None

        # function def
        if node.get("Function") == "def":
            return None

        # variable declaration
        if "datatype" in node and "identifier" in node:
            return self._check_declaration(node)

        ntype = node.get("type")
        # statements block
        if ntype == "Statements":
            return self._check_statements(node)
        # jumps
        if ntype == "jump statement":
            kw = node.get("keyword")
            if kw == "return":
                return self._check_return(node)
            if kw in ("break", "continue"):
                if self.loop_depth <= 0:
                    self._report(TypeChkError.ErroneousBreak, f"'{kw}' used outside loop", node)
                return None
            return None
        # conditional
        if ntype == "conditional statement":
            cond = node.get("args")
            ctype = self._check_node(cond)
            if ctype is None:
                self._report(TypeChkError.EmptyExpression, "Empty condition in conditional", node)
            elif not self._is_bool(ctype):
                self._report(TypeChkError.NonBooleanCondStmt, f"Condition must be boolean but got '{ctype}'", node)
            self.push_scope()
            self._check_node(node.get("body"))
            self.pop_scope()
            return None
        # iteration
        if ntype == "iteration":
            # args may be condition
            self.loop_depth += 1
            cond = node.get("args")
            if cond is None:
                self._report(TypeChkError.EmptyExpression, "Empty loop condition", node)
            else:
                ctype = self._check_node(cond)
                if ctype is not None and not self._is_bool(ctype):
                    self._report(TypeChkError.ExpectedBooleanExpression, f"Loop condition must be boolean got '{ctype}'", node)
            self.push_scope()
            self._check_node(node.get("body"))
            self.pop_scope()
            self.loop_depth -= 1
            return None

        # fn call in older style (type 'fn call') or new style FnCall
        if ntype == "fn call":
            return self._check_fncall_old(node)
        if node.get("type") == "FnCall":
            return self._check_fncall_new(node)

        # operator/expr nodes: support BinaryOp, UnaryOp, Identifier, Literal, or legacy OperatorExpression
        if node.get("type") in ("BinaryOp","UnaryOp","Identifier","Literal","OperatorExpression","PostfixExpression","ScanningExpression"):
            return self._check_expr_node(node)

        # fallback: walk children generically
        for k,v in node.items():
            if isinstance(v,(dict,list)):
                self._check_node(v)
        return None

    # ---------- declarations ----------
    def _check_declaration(self, node: Dict, is_global=False) -> Optional[str]:
        name = node.get("identifier")
        dtype = node.get("datatype")
        # create symbol locally
        sym = Symbol(name=name, kind="var", datatype=dtype, info={"node":node})
        if not is_global:
            self.declare_local(name, sym)
        # initializer
        val = node.get("value")
        if val is None:
            return dtype
        vtype = None
        if isinstance(val, dict):
            vtype = self._check_node(val)
        elif isinstance(val, str):
            vtype = self._infer_type_from_token(val)
            if vtype is None:
                # maybe identifier name
                s = self.find_symbol(val)
                vtype = s.datatype if s else None
        if vtype is None:
            self._report(TypeChkError.ErroneousVarDecl, f"Initializer type unknown for '{name}'", node)
        else:
            if not self._is_assignable(dtype, vtype):
                self._report(TypeChkError.ErroneousVarDecl, f"Cannot initialize '{name}' ({dtype}) with '{vtype}'", node)
        return dtype

    # ---------- statements ----------
    def _check_statements(self, node: Dict) -> None:
        self.push_scope()
        for stmt in node.get("block", []):
            self._check_node(stmt)
        self.pop_scope()
        return None

    # ---------- expressions ----------
    def _check_expr_node(self, node: Dict) -> Optional[str]:
        ntype = node.get("type")
        if ntype == "Literal":
            return node.get("literal_type") or "int"
        if ntype == "Identifier":
            name = node.get("name")
            sym = self.find_symbol(name)
            if sym is None:
                # possibly global fn name used as expr -> unknown
                self._report(TypeChkError.ExpressionTypeMismatch, f"Identifier '{name}' not declared", node)
                return None
            return sym.datatype
        if ntype == "UnaryOp":
            op = node.get("op")
            operand = node.get("operand")
            t = self._check_node(operand)
            if t is None:
                self._report(TypeChkError.ExpressionTypeMismatch, "Unary operand type unknown", node)
                return None
            if op in ('!','not'):
                if not self._is_bool(t):
                    self._report(TypeChkError.AttemptedBoolOpOnNonBools, f"Unary '!' on non-bool '{t}'", node)
                return "bool"
            if op in ('-','+','~'):
                if not self._is_numeric(t) and op != '~':
                    self._report(TypeChkError.ExpressionTypeMismatch, f"Unary '{op}' requires numeric operand, got '{t}'", node)
                return "float" if t=="float" else ("int" if t=="int" else None)
            return None
        if ntype == "BinaryOp":
            op = node.get("op")
            left = node.get("left")
            right = node.get("right")
            lt = self._check_node(left)
            rt = self._check_node(right)
            # if unknowns, try identifier lookup when string
            if lt is None and isinstance(left, str):
                s = self.find_symbol(left); lt = s.datatype if s else None
            if rt is None and isinstance(right, str):
                s = self.find_symbol(right); rt = s.datatype if s else None

            # empty expr
            if lt is None or rt is None:
                if lt is None or rt is None:
                    self._report(TypeChkError.EmptyExpression, f"Empty side in binary op '{op}'", node)
                    return None

            # boolean ops
            if op in ("&&","||","and","or"):
                if not self._is_bool(lt) or not self._is_bool(rt):
                    self._report(TypeChkError.AttemptedBoolOpOnNonBools, f"Boolean op '{op}' needs bools got '{lt}','{rt}'", node)
                return "bool"

            # bitwise: require int (we restrict to int)
            if op in ("&","|","^"):
                if not self._is_int(lt) or not self._is_int(rt):
                    self._report(TypeChkError.AttemptedBitOpOnNonNumeric, f"Bitwise '{op}' requires int operands got '{lt}','{rt}'", node)
                return "int" if self._is_int(lt) and self._is_int(rt) else None

            # shifts
            if op in ("<<", ">>"):
                if not self._is_int(lt) or not self._is_int(rt):
                    self._report(TypeChkError.AttemptedShiftOnNonInt, f"Shift '{op}' requires ints got '{lt}','{rt}'", node)
                return "int"

            # exponent
            if op in ("**",):
                if not self._is_numeric(lt) or not self._is_numeric(rt):
                    self._report(TypeChkError.AttemptedExponentiationOfNonNumeric, f"Exponent '{op}' needs numeric got '{lt}','{rt}'", node)
                return "float" if "float" in (lt,rt) else "int"

            # arithmetic
            if op in ("+","-","*","/","%"):
                if not self._is_numeric(lt) or not self._is_numeric(rt):
                    self._report(TypeChkError.AttemptedAddOpOnNonNumeric, f"Arithmetic '{op}' needs numeric got '{lt}','{rt}'", node)
                    return None
                return "float" if "float" in (lt,rt) else "int"

            # assignments (including compound)
            if op in ("=","+=","-=","*=","/="):
                # left must be identifier
                l_sym = None
                if isinstance(left, dict) and left.get("type") == "Identifier":
                    l_sym = self.find_symbol(left.get("name"))
                elif isinstance(left, str):
                    l_sym = self.find_symbol(left)
                if not l_sym:
                    self._report(TypeChkError.ExpressionTypeMismatch, f"Assignment to undeclared '{left}'", node)
                    return None
                # right type checked above (rt)
                if rt is None:
                    self._report(TypeChkError.ExpressionTypeMismatch, f"Right-hand side type unknown in assignment", node)
                    return None
                # for compound operators e.g. "+=" treat as binary op then assign
                target_type = l_sym.datatype
                if not self._is_assignable(target_type, rt):
                    self._report(TypeChkError.ExpressionTypeMismatch, f"Cannot assign '{rt}' to '{target_type}'", node)
                return target_type

            # comparisons -> bool
            if op in ("==","!=","<",">","<=",">="):
                # allow numeric-to-numeric or same type
                if (self._is_numeric(lt) and self._is_numeric(rt)) or (lt == rt and lt is not None):
                    return "bool"
                self._report(TypeChkError.ExpressionTypeMismatch, f"Comparison '{op}' between incompatible '{lt}' and '{rt}'", node)
                return "bool"

            # unknown operator
            self._report(TypeChkError.ExpressionTypeMismatch, f"Unknown operator '{op}'", node)
            return None

        # legacy OperatorExpression format (identifier/op/value)
        if node.get("type") == "OperatorExpression":
            left = node.get("identifier")
            right = node.get("value")
            op = node.get("op") or node.get("operator")
            # map to BinaryOp style and reuse
            fake = {'type':'BinaryOp','op':op,'left': left if isinstance(left, dict) else ( {'type':'Identifier','name':left} if isinstance(left,str) else left),'right': right if isinstance(right, dict) else ( {'type':'Identifier','name':right} if isinstance(right,str) else right)}
            return self._check_expr_node(fake)

        return None

    # ---------- function calls ----------
    def _check_fncall_new(self, node: Dict) -> Optional[str]:
        # node: {'type':'FnCall','name':str,'args':[ast,...]}
        fname = node.get("name")
        actual_args = node.get("args", [])
        f_sym = self.find_symbol(fname)
        if not f_sym or f_sym.kind != "func":
            self._report(TypeChkError.ExpressionTypeMismatch, f"Call to undefined function '{fname}'", node)
            return None
        fn_node = f_sym.info.get("node") if f_sym.info else None
        declared = []
        if fn_node:
            for p in fn_node.get("params", []):
                if isinstance(p,(list,tuple)) and p[0] == "Param":
                    declared.append(p[1])
        # param count
        if len(actual_args) != len(declared):
            self._report(TypeChkError.FnCallParamCount, f"Function '{fname}' expects {len(declared)} args got {len(actual_args)}", node)
        # check types
        for i,a in enumerate(actual_args):
            atype = None
            if isinstance(a, dict):
                atype = self._check_node(a)
            elif isinstance(a, str):
                atype = self._infer_type_from_token(a)
                if atype is None:
                    s = self.find_symbol(a); atype = s.datatype if s else None
            if i < len(declared) and declared[i] is not None and atype is not None:
                if not self._is_assignable(declared[i], atype):
                    self._report(TypeChkError.FnCallParamType, f"In call '{fname}' arg {i+1} expected '{declared[i]}' got '{atype}'", node)
        return fn_node.get("return type") if fn_node else None

    def _check_fncall_old(self,node: Dict)->Optional[str]:
        # old style: args = [("identifier","fname"), arg1, arg2,...]
        args = node.get("args",[])
        if not args:
            self._report(TypeChkError.EmptyExpression,"Empty function call",node); return None
        first = args[0]
        if isinstance(first, tuple) and first[0]=="identifier":
            fname = first[1]; actual_args = args[1:]
        elif isinstance(first, str):
            fname = first; actual_args = args[1:]
        else:
            fname = None; actual_args = args[1:]
        if fname:
            f_sym = self.find_symbol(fname)
            if not f_sym or f_sym.kind != "func":
                self._report(TypeChkError.ExpressionTypeMismatch,f"Call to undefined function '{fname}'",node); return None
            fn_node = f_sym.info.get("node") if f_sym.info else None
            declared = []
            if fn_node:
                for p in fn_node.get("params",[]):
                    if isinstance(p,(list,tuple)) and p[0]=="Param":
                        declared.append(p[1])
            if len(actual_args) != len(declared):
                self._report(TypeChkError.FnCallParamCount,f"Function '{fname}' expects {len(declared)} args got {len(actual_args)}",node)
            for i,a in enumerate(actual_args):
                atype = None
                if isinstance(a, tuple) and a[0]=="identifier":
                    s = self.find_symbol(a[1]); atype = s.datatype if s else None
                elif isinstance(a, dict):
                    atype = self._check_node(a)
                elif isinstance(a, str):
                    atype = self._infer_type_from_token(a)
                    if atype is None:
                        s = self.find_symbol(a); atype = s.datatype if s else None
                if i < len(declared) and declared[i] and atype and not self._is_assignable(declared[i], atype):
                    self._report(TypeChkError.FnCallParamType, f"In call '{fname}' arg {i+1} expected '{declared[i]}' got '{atype}'", node)
            return fn_node.get("return type") if fn_node else None
        return None

    # ---------- return ----------
    def _check_return(self,node: Dict)->Optional[str]:
        self.current_fn_has_return = True
        expr = node.get("args")
        if expr is None:
            if self.current_fn_ret and self.current_fn_ret != "void":
                self._report(TypeChkError.ErroneousReturnType, f"Function expects '{self.current_fn_ret}' but return has no value", node)
            return None
        t = None
        if isinstance(expr, dict):
            t = self._check_node(expr)
        elif isinstance(expr,str):
            t = self._infer_type_from_token(expr)
            if t is None:
                s = self.find_symbol(expr); t = s.datatype if s else None
        if self.current_fn_ret and t and not self._is_assignable(self.current_fn_ret, t):
            self._report(TypeChkError.ErroneousReturnType, f"Return type mismatch: expected '{self.current_fn_ret}', got '{t}'", node)
        return t

    # ---------- function wrapper ----------
    def _check_function(self, fn_node: Dict):
        self.current_fn_ret = fn_node.get("return type") or fn_node.get("rtype")
        self.current_fn_has_return = False
        self.push_scope()
        for p in fn_node.get("params",[]):
            if isinstance(p,(list,tuple)) and p[0]=="Param":
                _, ptype, pname = p
                if pname:
                    self.declare_local(pname, Symbol(name=pname, kind="param", datatype=ptype, info={"node":fn_node}))
        # check body
        self._check_node(fn_node.get("body"))
        # finalize
        if self.current_fn_ret and self.current_fn_ret != "void" and not self.current_fn_has_return:
            self._report(TypeChkError.ReturnStmtNotFound, f"Function '{fn_node.get('identifier')}' of type '{self.current_fn_ret}' has no return", fn_node)
        self.pop_scope()
        self.current_fn_ret = None
        self.current_fn_has_return = False

    # ---------- utilities ----------
    def _infer_type_from_token(self, token: str) -> Optional[str]:
        if token is None:
            return None
        s = token.strip()
        if s == "":
            return None
        if s.startswith('"') and s.endswith('"'):
            return "string"
        if s in ("true","false"):
            return "bool"
        try:
            if "." in s:
                float(s); return "float"
            else:
                int(s); return "int"
        except Exception:
            # identifier fallback
            sym = self.find_symbol(s)
            return sym.datatype if sym else None

    def _is_numeric(self,t):
        return t in self.numeric
    def _is_int(self,t):
        return t in self.int_only
    def _is_bool(self,t):
        return t in self.bools
    def _is_assignable(self,to_t,from_t):
        if to_t is None or from_t is None: return False
        if to_t == from_t: return True
        if to_t == "float" and from_t == "int": return True
        return False

    def _report(self,kind:TypeChkError,msg:str,node=None):
        self.errors.append(TypeErrorReport(kind,msg,node))
