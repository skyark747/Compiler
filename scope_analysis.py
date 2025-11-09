# scope_analyzer.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

class ScopeError(Enum):
    UndeclaredVariableAccessed = auto()
    UndefinedFunctionCalled = auto()
    VariableRedefinition = auto()
    FunctionPrototypeRedefinition = auto()

@dataclass
class Symbol:
    name: str
    kind: str         # 'var' | 'param' | 'func'
    datatype: Optional[str] = None
    info: Optional[dict] = None

class ScopeAnalyzer:
    """
    Traverses the AST produced by your parser (dict-based nodes) and:
      - Maintains a spaghetti stack (list of scope dicts)
      - Detects:
          * UndeclaredVariableAccessed
          * UndefinedFunctionCalled
          * VariableRedefinition (in same scope)
          * FunctionPrototypeRedefinition (redefining function in global scope)
    Returns:
      - symbols: the global symbol table (list/dict)
      - errors: list of tuples (ScopeError, message, ast_node_path(optional))
    """

    def __init__(self, builtins: Optional[List[str]] = None):
        
        # spaghetti stack: each entry is a dict name -> Symbol
        self.scopes: List[Dict[str, Symbol]] = []

        self.errors: List[Tuple[ScopeError, str, Optional[Any]]] = []

        self.builtins = set(builtins or ["print", "input"])

    def push_scope(self):
        self.scopes.append({})
    def pop_scope(self):
        if self.scopes:
            self.scopes.pop()
    def current_scope(self) -> Dict[str, Symbol]:
        return self.scopes[-1] if self.scopes else {}

    def find_symbol(self, name: str) -> Optional[Symbol]:
        """Search from innermost to outermost scope."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def declare_symbol(self, name: str, kind: str, datatype: Optional[str] = None, node: Optional[Any] = None):
        """
        Declare symbol in current scope. If name exists in current scope -> VariableRedefinition.
        For functions, current scope should be global scope.
        """
        cs = self.current_scope()
        if name in cs:
            if kind == "func":
                self.errors.append((ScopeError.FunctionPrototypeRedefinition,
                                    f"Function '{name}' redefined in the same (global) scope",
                                    node))
            else:
                self.errors.append((ScopeError.VariableRedefinition,
                                    f"Identifier '{name}' redefined in the same scope",
                                    node))
            return False
        cs[name] = Symbol(name=name, kind=kind, datatype=datatype, info={"node": node})
        return True

    def analyze_program(self, program_ast: List[dict]):
        """
        program_ast is expected to be the list returned by your parser's parse_program,
        i.e. a list of function dicts at top-level.
        """

        self.push_scope()

        for node in program_ast:
            if isinstance(node, dict) and node.get("Function") == "def":
                fname = node.get("identifier")
                self.declare_symbol(fname, kind="func", datatype=node.get("return type"), node=node)
            else:
                pass

        for node in program_ast:
            self._walk_top_level_node(node)

        global_symbols = self.scopes[0].copy() if self.scopes else {}

        # cleanup stack
        self.pop_scope()
        return global_symbols, self.errors

    # Node walkers
    def _walk_top_level_node(self, node: Any):
        if not isinstance(node, dict):
            return
        if node.get("Function") == "def":
            self._walk_function(node)
        else:
            return

    def _walk_function(self, func_node: Dict[str, Any]):
        self.push_scope()
        fname = func_node.get("identifier")
        params = func_node.get("params", [])

        # params are tuples like ("Param", type, name)
        for p in params:
            if isinstance(p, (list, tuple)) and p[0] == "Param":
                _, ptype, pname = p
                if pname is None:
                    continue
                self.declare_symbol(pname, kind="param", datatype=ptype, node=func_node)

        body = func_node.get("body")
        self._walk_node(body)
        self.pop_scope()

    def _walk_node(self, node: Any):
        """Generic dispatcher to walk node types."""
        if node is None:
            return
        if isinstance(node, list):
            for n in node:
                self._walk_node(n)
            return

        if not isinstance(node, dict):
            return

        ntype = node.get("type")
        if ntype == "Statements":
            self._walk_statements(node)
            return

        if "datatype" in node and "identifier" in node:
            self._walk_declaration(node)
            return

        # operator expression like {"type":"OperatorExpression","identifier": "i", "value": X}
        if node.get("type") == "OperatorExpression":
            self._walk_operator_expression(node)
            return

        # postfix expression like a->b or a.b
        if node.get("type") == "PostfixExpression":
            self._walk_postfix_expression(node)
            return

        # scanning expression (print/input)
        if node.get("type") == "ScanningExpression":
            self._walk_scanning_expression(node)
            return

        # jump statement (return, goto, or might wrap a function call)
        if node.get("type") == "jump statement":
            args = node.get("args")
            if isinstance(args, dict) and args.get("type") == "fn call":
                self._walk_function_call(args)
            return

        if node.get("type") == "fn call":
            self._walk_function_call(node)
            return

        # conditional or iteration nodes have 'body' or 'body'/'args'
        if node.get("type") in ("conditional statement", "iteration"):
            if args:
                self._walk_node(args)

            # body may be a single statement or a block
            body = node.get("body")
            if body is not None:
                # create scope for the block body
                self.push_scope()
                self._walk_node(body)
                self.pop_scope()
            return

        # class/struct-like nodes or other nodes
        for k, v in node.items():
            if isinstance(v, (dict, list)):
                self._walk_node(v)

    def _walk_statements(self, node: Dict[str, Any]):
        self.push_scope()
        stmts = node.get("block", [])
        for s in stmts:
            self._walk_node(s)
        self.pop_scope()

    def _walk_declaration(self, node: Dict[str, Any]):
        name = node.get("identifier")
        dtype = node.get("datatype")
        self.declare_symbol(name, kind="var", datatype=dtype, node=node)
        # If initializer references an identifier, check it
        val = node.get("value")
        if isinstance(val, str):
            # initializer could be identifier name or string literal; try to detect numeric vs identifier
            if not self._looks_like_literal(val):
                # treat as identifier usage
                self._check_variable_usage(val, node)
        elif isinstance(val, dict):
            self._walk_node(val)

    def _walk_operator_expression(self, node: Dict[str, Any]):
        left = node.get("identifier")
        right = node.get("value")
        # left is identifier used (written/read)
        if isinstance(left, str):
            self._check_variable_usage(left, node)
        # right may be identifier or literal
        if isinstance(right, str):
            if not self._looks_like_literal(right):
                self._check_variable_usage(right, node)
        elif isinstance(right, dict):
            self._walk_node(right)

    def _walk_postfix_expression(self, node: Dict[str, Any]):
        # left/right could be identifiers or keywords
        left = node.get("left")
        right = node.get("right")
        if isinstance(left, str):
            # left may be a variable/identifier (struct/object) or keyword; treat as identifier usage
            if left not in self.builtins:
                self._check_variable_usage(left, node)
        if isinstance(right, str):
            self._check_variable_usage(right, node)

    def _walk_scanning_expression(self, node: Dict[str, Any]):
        kw = node.get("keyword")
        if kw in ("print", "input"):
            # print/input are builtin; analyze args for identifiers used
            for arg in node.get("args", []):
                if isinstance(arg, dict):
                    self._walk_node(arg)
                elif isinstance(arg, str):
                    if not self._looks_like_literal(arg):
                        self._check_variable_usage(arg, node)
                elif isinstance(arg, tuple):
                    # check tuple returned by check_scans or parse_scanning_expression format
                    # e.g., ("identifier", "x")
                    if arg and arg[0] == "identifier":
                        self._check_variable_usage(arg[1], node)
        else:
            for arg in node.get("args", []):
                self._walk_node(arg)

    def _walk_function_call(self, node: Dict[str, Any]):
        args = node.get("args", [])
        if not args:
            return
        # heuristic: first argument tuple indicates function name in your parser
        first = args[0]
        fname = None
        if isinstance(first, tuple) and len(first) >= 2 and first[0] == "identifier":
            fname = first[1]
        elif isinstance(first, dict) and first.get("type") == "PostfixExpression":
            pass
        elif isinstance(first, str):
            fname = first

        if fname:
            # check if function defined in any scope (global)
            sym = self.find_symbol(fname)
            if not sym or sym.kind != "func":
                if fname not in self.builtins:
                    self.errors.append((ScopeError.UndefinedFunctionCalled,
                                        f"Function '{fname}' called but not defined",
                                        node))
        # check other args (they may be identifiers)
        for a in args[1:]:
            if isinstance(a, tuple) and a[0] == "identifier":
                self._check_variable_usage(a[1], node)
            elif isinstance(a, dict):
                self._walk_node(a)

    ###### Utilities ######

    def _check_variable_usage(self, name: str, node: Any):
        # If not declared in any accessible scope, error
        sym = self.find_symbol(name)
        # If found and its kind is 'func' but used as variable, that may be another error in type-check phase.
        if sym is None:
            # Not found
            self.errors.append((ScopeError.UndeclaredVariableAccessed,
                                f"Identifier '{name}' used but not declared in any accessible scope",
                                node))

    def _looks_like_literal(self, token_str: str) -> bool:
        # numeric literals are digits, string literals begin with quotes
        if not isinstance(token_str, str):
            return False
        token_str = token_str.strip()
        if token_str.startswith('"') and token_str.endswith('"'):
            return True
        # integers
        if all(ch.isdigit() for ch in token_str):
            return True
        # floats
        try:
            float(token_str)
            return True
        except Exception:
            return False
