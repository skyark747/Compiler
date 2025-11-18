# scope_analyzer.py (extended version)
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


##### Error & Warning Definitions #####

class ScopeError(Enum):
    UndeclaredVariableAccessed = auto()
    UndefinedFunctionCalled = auto()
    VariableRedefinition = auto()
    FunctionPrototypeRedefinition = auto()
    ParameterRedefinition = auto()
    InvalidReturnOutsideFunction = auto()
    BreakOrContinueOutsideLoop = auto()
    RedeclarationWithDifferentType = auto()
    LabelRedefinition = auto()
    UndefinedLabel = auto()
    UnreachableDeclaration = auto()


class ScopeWarning(Enum):
    ShadowingWarning = auto()
    UnusedVariableWarning = auto()


##### Symbol and Scope Structures #####

@dataclass
class Symbol:
    name: str
    kind: str             # 'var', 'param', 'func', 'label'
    datatype: Optional[str] = None
    info: Optional[dict] = None
    is_used: bool = False


class ScopeAnalyzer:
    def __init__(self, builtins: Optional[List[str]] = None):
        self.scopes: List[Dict[str, Symbol]] = []
        self.errors: List[Tuple[ScopeError, str, Optional[Any]]] = []
        self.warnings: List[Tuple[ScopeWarning, str, Optional[Any]]] = []
        self.loop_depth: int = 0
        self.in_function: bool = False
        self.labels_defined: set[str] = set()
        self.labels_used: set[str] = set()
        self.builtins = set(builtins or ["print", "input"])

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        if self.scopes:
            scope = self.scopes.pop()
            # Check for unused variable warnings on exit
            for sym in scope.values():
                if sym.kind in ("var", "param") and not sym.is_used:
                    self.warnings.append(
                        (ScopeWarning.UnusedVariableWarning, f"'{sym.name}' declared but never used", sym.info)
                    )

    def current_scope(self) -> Dict[str, Symbol]:
        return self.scopes[-1] if self.scopes else {}

    def find_symbol(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def declare_symbol(self, name: str, kind: str, datatype: Optional[str] = None, node: Optional[Any] = None):
        cs = self.current_scope()

        if name in cs:
            # Same-scope redefinitions
            if kind == "func":
                self.errors.append((ScopeError.FunctionPrototypeRedefinition, f"Function '{name}' redefined", node))
            elif kind == "param":
                self.errors.append((ScopeError.ParameterRedefinition, f"Parameter '{name}' redefined", node))
            elif datatype and cs[name].datatype and datatype != cs[name].datatype:
                self.errors.append((ScopeError.RedeclarationWithDifferentType,
                                    f"Variable '{name}' redeclared with different type", node))
            else:
                self.errors.append((ScopeError.VariableRedefinition, f"Identifier '{name}' redefined", node))
            return False

        # Shadowing warning
        outer = self.find_symbol(name)
        if outer and kind in ("var", "param") and outer.kind in ("var", "param"):
            self.warnings.append((ScopeWarning.ShadowingWarning,
                                  f"'{name}' shadows outer variable declared earlier", node))

        cs[name] = Symbol(name=name, kind=kind, datatype=datatype, info={"node": node})
        return True

##### Main Analysis Entry #####

    def analyze_program(self, program_ast: List[dict]):
        self.push_scope()  # global scope

        # First pass: register global functions
        for node in program_ast:
            if isinstance(node, dict) and node.get("Function") == "def":
                fname = node.get("identifier")
                self.declare_symbol(fname, "func", node.get("return type"), node)

        # Second pass: analyze bodies
        for node in program_ast:
            self._walk_node(node)

        # Undefined labels
        for used in self.labels_used:
            if used not in self.labels_defined:
                self.errors.append((ScopeError.UndefinedLabel, f"Label '{used}' used but not defined", None))

        global_symbols = self.scopes[0].copy()
        self.pop_scope()
        return global_symbols, self.errors, self.warnings

    def _walk_node(self, node: Any):
        if node is None:
            return

        if isinstance(node, list):
            for n in node:
                self._walk_node(n)
            return

        if not isinstance(node, dict):
            return

        ntype = node.get("type")
        func = node.get("Function")

        # Function definition
        if func == "def":
            self._walk_function(node)
            return

        # Statements block
        if ntype == "Statements":
            self._walk_statements(node)
            return

        # Declarations
        if "datatype" in node and "identifier" in node:
            self._walk_declaration(node)
            return

        # Control structures
        if ntype == "iteration":
            self.loop_depth += 1
            self._walk_node(node.get("args"))
            self.push_scope()
            self._walk_node(node.get("body"))
            self.pop_scope()
            self.loop_depth -= 1
            return

        if ntype == "conditional statement":
            self._walk_node(node.get("args"))
            self.push_scope()
            self._walk_node(node.get("body"))
            self.pop_scope()
            return

        # Jump statements
        if ntype == "jump statement":
            kw = node.get("keyword")
            if kw == "return":
                if not self.in_function:
                    self.errors.append((ScopeError.InvalidReturnOutsideFunction,
                                        "Return statement outside of a function", node))
            elif kw in ("break", "continue"):
                if self.loop_depth == 0:
                    self.errors.append((ScopeError.BreakOrContinueOutsideLoop,
                                        f"'{kw}' used outside of loop", node))
            elif kw == "goto":
                label = node.get("args")
                if isinstance(label, str):
                    self.labels_used.add(label)
            return

        # Label definitions
        if ntype == "label":
            label_name = node.get("identifier")
            if label_name in self.labels_defined:
                self.errors.append((ScopeError.LabelRedefinition, f"Label '{label_name}' redefined", node))
            else:
                self.labels_defined.add(label_name)
            return

        # Function call
        if ntype == "fn call":
            self._walk_function_call(node)
            return

        # Operator or scanning expressions
        if ntype in ("OperatorExpression", "ScanningExpression", "PostfixExpression"):
            self._walk_expression(node)
            return

        # Generic recursive fallback
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                self._walk_node(v)

##### Walkers #####

    def _walk_function(self, func_node: dict):
        fname = func_node.get("identifier")
        params = func_node.get("params", [])

        self.in_function = True
        self.push_scope()

        # Parameters
        for p in params:
            if isinstance(p, (tuple, list)) and p[0] == "Param":
                _, ptype, pname = p
                if pname:
                    self.declare_symbol(pname, "param", ptype, func_node)

        # Body
        self._walk_node(func_node.get("body"))

        # Exit function
        self.pop_scope()
        self.in_function = False

    def _walk_statements(self, node: dict):
        stmts = node.get("block", [])
        self.push_scope()
        for stmt in stmts:
            self._walk_node(stmt)
        self.pop_scope()

    def _walk_declaration(self, node: dict):
        name = node.get("identifier")
        dtype = node.get("datatype")
        self.declare_symbol(name, "var", dtype, node)

        # initializer
        val = node.get("value")
        if isinstance(val, str) and not self._looks_like_literal(val):
            self._check_variable_usage(val, node)
        elif isinstance(val, dict):
            self._walk_node(val)

    def _walk_function_call(self, node: dict):
        args = node.get("args", [])
        fname = None

        if args and isinstance(args[0], tuple) and args[0][0] == "identifier":
            fname = args[0][1]
        elif isinstance(args[0], str):
            fname = args[0]

        if fname and fname not in self.builtins:
            sym = self.find_symbol(fname)
            if not sym or sym.kind != "func":
                self.errors.append((ScopeError.UndefinedFunctionCalled,
                                    f"Function '{fname}' called but not defined", node))

        # analyze argument expressions
        for a in args[1:]:
            if isinstance(a, tuple) and a[0] == "identifier":
                self._check_variable_usage(a[1], node)
            elif isinstance(a, dict):
                self._walk_node(a)

    def _walk_expression(self, node: dict):
        for k, v in node.items():
            if isinstance(v, str) and not self._looks_like_literal(v):
                self._check_variable_usage(v, node)
            elif isinstance(v, (dict, list)):
                self._walk_node(v)

##### Utilities #####

    def _check_variable_usage(self, name: str, node: Any):
        sym = self.find_symbol(name)
        if not sym:
            self.errors.append((ScopeError.UndeclaredVariableAccessed,
                                f"Identifier '{name}' used before declaration", node))
        else:
            sym.is_used = True

    def _looks_like_literal(self, val: str) -> bool:
        if not isinstance(val, str):
            return False
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            return True
        if val.isdigit():
            return True
        try:
            float(val)
            return True
        except Exception:
            return False
