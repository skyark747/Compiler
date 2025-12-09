# ir_generator.py
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Sequence, Union
import itertools

# Try optional LLVM backend
try:
    import llvmlite.ir as llir
    import llvmlite.binding as llvm
    HAS_LLVM = True
except Exception:
    HAS_LLVM = False


# ---------- Errors ----------
class IRGenErrorCode(Enum):
    UnknownIdentifier = auto()
    TypeMismatch = auto()
    UnsupportedNode = auto()
    MalformedExpression = auto()
    FunctionNotFound = auto()
    Other = auto()


@dataclass
class IRGenError:
    code: IRGenErrorCode
    message: str
    node: Optional[Any] = None


# ---------- IR Data Structures (TAC-like) ----------
@dataclass
class Temp:
    name: str

    def __str__(self):
        return self.name


@dataclass
class Label:
    name: str

    def __str__(self):
        return f"{self.name}:"


@dataclass
class Instr:
    op: str
    dest: Optional[str]
    args: List[str]
    comment: Optional[str] = None

    def to_text(self) -> str:
        left = f"{self.dest} = " if self.dest else ""
        args_text = ", ".join(self.args)
        comment = f"  # {self.comment}" if self.comment else ""
        return f"{left}{self.op} {args_text}{comment}"


@dataclass
class BasicBlock:
    label: Label
    instrs: List[Instr]

    def __init__(self, label: Label):
        self.label = label
        self.instrs = []

    def emit(self, instr: Instr):
        self.instrs.append(instr)


@dataclass
class FunctionIR:
    name: str
    params: List[Tuple[str, str]]  # (name, type)
    ret_type: Optional[str]
    blocks: List[BasicBlock]

    def __init__(self, name: str, params: List[Tuple[str, str]], ret_type: Optional[str]):
        self.name = name
        self.params = params
        self.ret_type = ret_type
        self.blocks = []


# ---------- IR Generator ----------
class IRGenerator:
    def __init__(self, ast: List[dict], symbol_table: Optional[List[Dict[str, Any]]] = None):
        """
        ast: program AST (list of top-level nodes)
        symbol_table: list of scope dicts outer->inner OR a single dict of globals
        """
        self.ast = ast
        # Accept various symbol_table shapes: None, single dict, or list-of-dicts
        if symbol_table is None:
            self.symbol_table = []
        elif isinstance(symbol_table, dict):
            self.symbol_table = [symbol_table]
        else:
            self.symbol_table = symbol_table

        self.errors: List[IRGenError] = []

        # temp and label counters
        self._temp_counter = itertools.count()
        self._label_counter = itertools.count()

        # functions map name -> FunctionIR
        self.functions: Dict[str, FunctionIR] = {}
        # current function & block being emitted
        self._current_fn: Optional[FunctionIR] = None
        self._current_block: Optional[BasicBlock] = None

        # builtins (for call lowering decisions) - you can extend
        self.builtins = {"print", "input"}

        # convenience: primitive types mapping (from typechecker)
        self.primitive_types = {"int", "float", "bool", "string", "void", "char"}

    # ---------- helpers ----------
    def new_temp(self) -> Temp:
        return Temp(f"t{next(self._temp_counter)}")

    def new_label(self, base: str = "L") -> Label:
        return Label(f"{base}{next(self._label_counter)}")

    def emit_instr(self, op: str, dest: Optional[str], args: List[str], comment: Optional[str] = None):
        if self._current_block is None:
            # auto-create anonymous block if needed
            self._current_block = BasicBlock(self.new_label("entry"))
            if self._current_fn:
                self._current_fn.blocks.append(self._current_block)
        instr = Instr(op=op, dest=dest, args=args, comment=comment)
        assert self._current_block is not None
        self._current_block.emit(instr)
        return instr

    def add_function(self, name: str, params: List[Tuple[str, str]], ret_type: Optional[str]) -> FunctionIR:
        if name in self.functions:
            # overwrite allowed, but report
            self.errors.append(IRGenError(IRGenErrorCode.Other, f"Function '{name}' redefined"))
        fn = FunctionIR(name, params, ret_type)
        self.functions[name] = fn
        return fn

    def enter_function(self, fn: FunctionIR):
        self._current_fn = fn
        # entry block must exist
        entry_label = Label(f"{fn.name}_entry")
        entry = BasicBlock(entry_label)
        fn.blocks.append(entry)
        self._current_block = entry

    def leave_function(self):
        self._current_fn = None
        self._current_block = None

    def find_symbol(self, name: str) -> Optional[Any]:
        # search symbol_table from inner -> outer
        for scope in reversed(self.symbol_table):
            if name in scope:
                return scope[name]
        # not found
        return None

    # ---------- main pass ----------
    def generate(self):
        """
        Walk top-level AST nodes, generate FunctionIRs + global data as needed.
        """
        for node in self.ast:
            if not isinstance(node, dict):
                continue
            # Function definitions
            if node.get("Function") == "def":
                fname = node.get("identifier")
                rtype = node.get("return type") or node.get("rtype") or "void"
                params = []
                for p in node.get("params", []):
                    if isinstance(p, (list, tuple)) and len(p) >= 3 and p[0] == "Param":
                        _, ptype, pname = p
                        params.append((pname, ptype))
                fn_ir = self.add_function(fname, params, rtype)
                self.enter_function(fn_ir)
                # parameter mapping: for now we emit assigns from param names to temps (optional)
                for pname, ptype in params:
                    # no-op in TAC: parameters are accessible by name
                    pass
                # walk body
                self._gen_node(node.get("body"))
                # ensure function ends with return (if not explicit, add `ret void` or `ret 0` depending)
                last_block = self._current_block
                if last_block and (not last_block.instrs or last_block.instrs[-1].op != "ret"):
                    # add implicit return for void functions
                    if rtype == "void":
                        self.emit_instr("ret", None, [])
                    else:
                        # return a zero-like literal for ints/floats/bools/strings: conservative ret 0
                        tmp = self.new_temp()
                        self.emit_instr("const", str(tmp), ["0"], comment="implicit return default")
                        self.emit_instr("ret", None, [str(tmp)])
                self.leave_function()

            # global var decl -> emit as single-instruction init if a value exists
            elif "datatype" in node and "identifier" in node:
                name = node.get("identifier")
                dtype = node.get("datatype")
                val = node.get("value")
                # for global storage we could record it; here we emit an init pseudo-instr
                if val is not None:
                    if isinstance(val, dict):
                        tv = self._gen_expr(val)
                        if tv:
                            self.emit_instr("global_init", name, [tv], comment=f"init {dtype} {name}")
                    elif isinstance(val, str):
                        tv = self._gen_expr({'type':'Literal','value':val,'literal_type':('string' if val.startswith('"') else 'int')})
                        if tv:
                            self.emit_instr("global_init", name, [tv], comment=f"init {dtype} {name}")
                else:
                    self.emit_instr("global_decl", name, [dtype], comment=f"declare {dtype} {name}")

            else:
                # top-level statement (maybe immediate expression or fn call)
                self._gen_node(node)

        return self.functions, self.errors

    # ---------- node generator ----------
    def _gen_node(self, node: Any) -> Optional[str]:
        # returns a temp or literal textual representation when relevant
        if node is None:
            return None
        if isinstance(node, list):
            last = None
            for n in node:
                last = self._gen_node(n)
            return last
        if not isinstance(node, dict):
            # raw token -> literal or identifier name
            if isinstance(node, str):
                if node.startswith('"') and node.endswith('"'):
                    t = self.new_temp()
                    self.emit_instr("const", str(t), [node])
                    return str(t)
                # else identifier -> just return name (use as operand)
                return node
            return None

        # Statements block
        ntype = node.get("type")
        if ntype == "Statements":
            # create a new nested block in TAC? We'll just emit sequentially
            for s in node.get("block", []):
                self._gen_node(s)
            return None

        # label
        if ntype == "label":
            lname = node.get("identifier") or f"lbl{next(self._label_counter)}"
            lab = Label(lname)
            # append new block with that label
            bb = BasicBlock(lab)
            assert self._current_fn is not None, "Label only allowed inside functions"
            self._current_fn.blocks.append(bb)
            self._current_block = bb
            return None

        # jump statement
        if ntype == "jump statement":
            kw = node.get("keyword")
            if kw == "return":
                arg = node.get("args")
                if arg is None:
                    self.emit_instr("ret", None, [])
                else:
                    tmp = self._gen_expr(arg) if isinstance(arg, dict) else (arg if isinstance(arg, str) else None)
                    if tmp is None:
                        # fallback: produce literal zero
                        tmp = str(self.new_temp())
                        self.emit_instr("const", tmp, ["0"], comment="fallback return")
                    self.emit_instr("ret", None, [tmp])
                return None
            if kw == "goto":
                target = node.get("args")
                if isinstance(target, str):
                    self.emit_instr("jmp", None, [target])
                else:
                    self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, "goto target not a string", node))
                return None
            if kw in ("break","continue"):
                # assume structured loops produce labels in higher level; generator should have added jumps
                # here we just emit a generic pseudo-instruction (user can later lower)
                self.emit_instr(kw, None, [])
                return None
            return None

        # iteration and conditionals
        if ntype == "iteration":
            # expect 'args' as condition expr, and 'body' as node
            # generate labels for loop header, body and exit
            header = self.new_label("loop_h")
            body_label = self.new_label("loop_b")
            end_label = self.new_label("loop_end")
            # jump to header
            self.emit_instr("jmp", None, [str(header.name)])
            # header label
            bb_header = BasicBlock(header)
            assert self._current_fn is not None
            self._current_fn.blocks.append(bb_header)
            self._current_block = bb_header
            cond = node.get("args")
            cond_tmp = self._gen_expr(cond) if cond else None
            if cond_tmp is None:
                # fallback: treat as true
                cond_tmp = str(self.new_temp())
                self.emit_instr("const", cond_tmp, ["1"], comment="loop cond fallback true")
            # conditional jump to body or end
            self.emit_instr("cjmp", None, [cond_tmp, str(body_label.name), str(end_label.name)])
            # body block
            bb_body = BasicBlock(body_label)
            self._current_fn.blocks.append(bb_body)
            self._current_block = bb_body
            self._gen_node(node.get("body"))
            # at end of body jump back to header
            self.emit_instr("jmp", None, [str(header.name)])
            # create end block
            bb_end = BasicBlock(end_label)
            self._current_fn.blocks.append(bb_end)
            self._current_block = bb_end
            return None

        if ntype == "conditional statement":
            # simple if-then(-else)
            cond = node.get("args")
            then_node = node.get("body")
            else_node = node.get("else")
            then_label = self.new_label("then")
            end_label = self.new_label("ifend")
            else_label = self.new_label("else") if else_node else end_label
            cond_tmp = self._gen_expr(cond)
            if cond_tmp is None:
                # treat unknown as false
                cond_tmp = str(self.new_temp())
                self.emit_instr("const", cond_tmp, ["0"], comment="cond fallback")
            self.emit_instr("cjmp", None, [cond_tmp, str(then_label.name), str(else_label.name)])
            # then
            bb_then = BasicBlock(then_label)
            assert self._current_fn is not None
            self._current_fn.blocks.append(bb_then)
            self._current_block = bb_then
            self._gen_node(then_node)
            self.emit_instr("jmp", None, [str(end_label.name)])
            # else
            if else_node:
                bb_else = BasicBlock(else_label)
                self._current_fn.blocks.append(bb_else)
                self._current_block = bb_else
                self._gen_node(else_node)
                self.emit_instr("jmp", None, [str(end_label.name)])
            # end
            bb_end = BasicBlock(end_label)
            self._current_fn.blocks.append(bb_end)
            self._current_block = bb_end
            return None

        # declarations - local var
        if "datatype" in node and "identifier" in node:
            name = node.get("identifier")
            val = node.get("value")
            if val is not None:
                if isinstance(val, dict):
                    tv = self._gen_expr(val)
                    if tv:
                        self.emit_instr("assign", name, [tv])
                elif isinstance(val, str):
                    # literal or symbol
                    if val.startswith('"') and val.endswith('"'):
                        tmp = self.new_temp()
                        self.emit_instr("const", str(tmp), [val])
                        self.emit_instr("assign", name, [str(tmp)])
                    else:
                        # identifier
                        self.emit_instr("assign", name, [val])
            else:
                # default init
                self.emit_instr("assign", name, ["0"], comment="default init")
            return None

        # function call old/new style inside statement/expression
        if node.get("type") == "FnCall" or node.get("type") == "fn call":
            return self._gen_call_node(node)

        # operator / expression nodes
        if node.get("type") in ("BinaryOp", "UnaryOp", "Identifier", "Literal", "OperatorExpression", "PostfixExpression", "ScanningExpression"):
            return self._gen_expr(node)

        # unknown
        self.errors.append(IRGenError(IRGenErrorCode.UnsupportedNode, f"Unsupported node for IR generation: {node.get('type')}", node))
        return None

    # ---------- expression lowering ----------
    def _gen_expr(self, expr: Any) -> Optional[str]:
        """
        Returns a temp name or literal textual value representing the expression result.
        """
        if expr is None:
            return None
        if isinstance(expr, str):
            if expr.startswith('"') and expr.endswith('"'):
                tmp = self.new_temp()
                self.emit_instr("const", str(tmp), [expr])
                return str(tmp)
            # identifier: return name directly (TAC uses names as operands)
            return expr

        if not isinstance(expr, dict):
            return None

        etype = expr.get("type")

        if etype == "Literal":
            lit_type = expr.get("literal_type") or "int"
            val = expr.get("value")
            tmp = self.new_temp()
            # we store literal as string in arg list
            self.emit_instr("const", str(tmp), [str(val)])
            return str(tmp)

        if etype == "Identifier":
            return expr.get("name")

        if etype == "UnaryOp":
            op = expr.get("op")
            operand = expr.get("operand")
            opd = self._gen_expr(operand)
            if opd is None:
                self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, f"Unary operand malformed for op {op}", expr))
                return None
            res = self.new_temp()
            # represent unary ops as 'neg tX' or 'not tX'
            if op in ("u-","-"):
                self.emit_instr("neg", str(res), [opd])
            elif op in ("u+","+"):
                # no-op
                self.emit_instr("mov", str(res), [opd])
            elif op in ("!","not"):
                self.emit_instr("not", str(res), [opd])
            else:
                self.emit_instr(f"un_{op}", str(res), [opd])
            return str(res)

        if etype == "BinaryOp":
            op = expr.get("op")
            left = expr.get("left")
            right = expr.get("right")
            ltmp = self._gen_expr(left) if isinstance(left, dict) else (left if isinstance(left, str) else None)
            rtmp = self._gen_expr(right) if isinstance(right, dict) else (right if isinstance(right, str) else None)
            if ltmp is None and isinstance(left, dict):
                self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, "Left operand generation failed", expr))
            if rtmp is None and isinstance(right, dict):
                self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, "Right operand generation failed", expr))

            # If one of operands is a literal string like '"hello"', ensure it is in temp form
            def ensure_temp(x):
                if x is None:
                    return None
                if isinstance(x, str) and x.startswith('"') and x.endswith('"'):
                    t = self.new_temp()
                    self.emit_instr("const", str(t), [x])
                    return str(t)
                return x

            ltmp = ensure_temp(ltmp)
            rtmp = ensure_temp(rtmp)

            res = self.new_temp()
            # map operators into TAC op names
            op_map = {
                '+':'add','-':'sub','*':'mul','/':'div','%':'mod',
                '==':'eq','!=':'neq','<':'lt','>':'gt','<=':'le','>=':'ge',
                '&&':'and','||':'or','&':'band','|':'bor','^':'bxor',
                '<<':'shl','>>':'shr','**':'pow',
                '=':'assign','+=':'add_assign','-=':'sub_assign',
            }

            if op in ('='):
                # assignment special-case: dest is left identifier
                dest_name = None
                if isinstance(left, dict) and left.get("type") == "Identifier":
                    dest_name = left.get("name")
                elif isinstance(left, str):
                    dest_name = left
                if dest_name is None:
                    self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, f"Left side of assignment is not assignable: {left}", expr))
                    return None
                # produce assign dest = rtmp
                self.emit_instr("assign", dest_name, [rtmp])
                return dest_name

            mapped = op_map.get(op)
            if mapped is None:
                mapped = f"op_{op}"
            # For boolean conditional ops we may want to produce 0/1 ints
            self.emit_instr(mapped, str(res), [ltmp or "0", rtmp or "0"])
            return str(res)

        if etype == "FnCall":
            return self._gen_call_node(expr)

        # legacy fn call style 'fn call'
        if expr.get("type") == "fn call":
            return self._gen_call_node(expr)

        # fallback: unsupported expression form
        self.errors.append(IRGenError(IRGenErrorCode.UnsupportedNode, f"Unsupported expression type: {etype}", expr))
        return None

    # ---------- call lowering ----------
    def _gen_call_node(self, node: Dict) -> Optional[str]:
        """
        Accepts two shapes:
         - new: {'type':'FnCall','name':str,'args':[ast,...]}
         - old: {'type':'fn call','args':[('identifier','fname'), arg1, arg2,...]}
        """
        if node.get("type") == "FnCall":
            fname = node.get("name")
            args = node.get("args", [])
            arg_temps = []
            for a in args:
                at = self._gen_expr(a) if isinstance(a, dict) else (a if isinstance(a, str) else None)
                if at is None:
                    # attempt token fallback
                    if isinstance(a, str):
                        arg_temps.append(a)
                    else:
                        self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, f"Could not generate arg for call {fname}", a))
                else:
                    arg_temps.append(at)
            # Builtin handling: map print to a special instruction
            if fname in self.builtins:
                # For TAC we emit builtin_<name> targs...
                dest = None
                if fname == "input":
                    # returns string
                    tmp = self.new_temp()
                    self.emit_instr("builtin_input", str(tmp), [])
                    return str(tmp)
                if fname == "print":
                    self.emit_instr("builtin_print", None, arg_temps)
                    return None
                self.emit_instr(f"builtin_{fname}", None, arg_temps)
                return None

            # user function: call instruction, produce temp for result if non-void
            fn_sym = self.find_symbol(fname)
            ret_temp = None
            if fn_sym:
                ret_type = getattr(fn_sym, "datatype", None) or (fn_sym.info.get("node", {}).get("return type") if fn_sym.info else None)
                # create temps for args if necessary (in TAC args can be names or temps)
                # emit: param tX ; call fname, nargs ; ret -> tY
                for at in arg_temps:
                    self.emit_instr("param", None, [at])
                if ret_type and ret_type != "void":
                    ret_temp = self.new_temp()
                    self.emit_instr("call", str(ret_temp), [fname, str(len(arg_temps))])
                    return str(ret_temp)
                else:
                    self.emit_instr("call", None, [fname, str(len(arg_temps))])
                    return None
            else:
                # Unknown function; emit call but report
                for at in arg_temps:
                    self.emit_instr("param", None, [at])
                tmp = self.new_temp()
                self.emit_instr("call", str(tmp), [fname, str(len(arg_temps))])
                self.errors.append(IRGenError(IRGenErrorCode.FunctionNotFound, f"Call to unknown function '{fname}'", node))
                return str(tmp)

        # old-style
        args = node.get("args", [])
        if not args:
            self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, "Empty fn call args", node))
            return None
        first = args[0]
        if isinstance(first, tuple) and first[0] == "identifier":
            fname = first[1]
            arg_list = args[1:]
        elif isinstance(first, str):
            fname = first
            arg_list = args[1:]
        else:
            self.errors.append(IRGenError(IRGenErrorCode.MalformedExpression, "Unknown fn call shape", node))
            return None
        # lower similarly to new style
        arg_temps = []
        for a in arg_list:
            if isinstance(a, tuple) and a[0] == "identifier":
                arg_temps.append(a[1])
            elif isinstance(a, dict):
                arg_temps.append(self._gen_expr(a))
            elif isinstance(a, str):
                if a.startswith('"') and a.endswith('"'):
                    tt = self.new_temp()
                    self.emit_instr("const", str(tt), [a])
                    arg_temps.append(str(tt))
                else:
                    arg_temps.append(a)
            else:
                arg_temps.append(None)
        fn_sym = self.find_symbol(fname)
        if fn_sym:
            ret_type = getattr(fn_sym, "datatype", None) or (fn_sym.info.get("node", {}).get("return type") if fn_sym.info else None)
        else:
            ret_type = None
            self.errors.append(IRGenError(IRGenErrorCode.FunctionNotFound, f"Call to unknown function '{fname}'", node))
        for at in arg_temps:
            if at is None:
                at = "0"
            self.emit_instr("param", None, [at])
        if ret_type and ret_type != "void":
            res = self.new_temp()
            self.emit_instr("call", str(res), [fname, str(len(arg_temps))])
            return str(res)
        else:
            self.emit_instr("call", None, [fname, str(len(arg_temps))])
            return None

    # ---------- textual emission ----------
    def to_text(self) -> str:
        lines = []
        for fname, fn in self.functions.items():
            lines.append(f"func {fname}({', '.join([n+':'+t for n,t in fn.params])}) -> {fn.ret_type or 'void'}")
            for bb in fn.blocks:
                lines.append(f"{bb.label.name}:")
                for instr in bb.instrs:
                    lines.append("  " + instr.to_text())
            lines.append("")  # blank line between functions
        return "\n".join(lines)

    # ---------- optional LLVM backend (very small) ----------
    def to_llvmlite_module(self) -> Optional[Tuple["llir.Module", bytes]]:
        """
        Try to convert simple arithmetic functions to an llvmlite Module and return (module, bitcode).
        This is a best-effort minimal backend and only supports a tiny subset:
          - integer arithmetic, function params as i64, return i64, simple returns and calls
        If llvmlite is not available returns None.
        """
        if not HAS_LLVM:
            self.errors.append(IRGenError(IRGenErrorCode.Other, "llvmlite not available; LLVM backend disabled"))
            return None

        module = llir.Module(name="module")
        int_t = llir.IntType(64)
        func_map = {}

        # Create function prototypes
        for fname, fn in self.functions.items():
            param_ts = [int_t for _ in fn.params]
            ret_t = int_t if (fn.ret_type and fn.ret_type != "void") else llir.VoidType()
            fnty = llir.FunctionType(ret_t, param_ts)
            func = llir.Function(module, fnty, name=fname)
            func_map[fname] = (fn, func)

        # Lower each function (very restricted: only integer ops and returns supported)
        for fname, (fn_ir, llfn) in func_map.items():
            block = llfn.append_basic_block("entry")
            builder = llir.IRBuilder(block)
            # map params to local names
            local_map = {}
            for i, (pname, ptype) in enumerate(fn_ir.params):
                arg = llfn.args[i]
                arg.name = pname
                local_map[pname] = arg

            # Very naive: walk instructions and emit matching IR for supported ops
            for bb in fn_ir.blocks:
                for instr in bb.instrs:
                    op = instr.op
                    args = instr.args
                    dest = instr.dest
                    try:
                        if op == "const" and dest:
                            # numeric constant
                            v = args[0]
                            try:
                                iv = int(v)
                                val = llir.Constant(int_t, iv)
                                alloca = builder.alloca(int_t, name=dest)
                                builder.store(val, alloca)
                                local_map[dest] = builder.load(alloca)
                            except Exception:
                                # skip non-int
                                pass
                        elif op in ("add","sub","mul","div","mod") and dest:
                            a = local_map.get(args[0], None)
                            b = local_map.get(args[1], None)
                            if a is None or b is None:
                                # try constants
                                def load_operand(x):
                                    if isinstance(x, str) and x.startswith("t"):
                                        return local_map.get(x)
                                    try:
                                        return llir.Constant(int_t, int(x))
                                    except Exception:
                                        return None
                                a = load_operand(args[0])
                                b = load_operand(args[1])
                            if a is None or b is None:
                                continue
                            if op == "add":
                                res = builder.add(a, b, name=dest)
                            elif op == "sub":
                                res = builder.sub(a, b, name=dest)
                            elif op == "mul":
                                res = builder.mul(a, b, name=dest)
                            elif op == "div":
                                res = builder.sdiv(a, b, name=dest)
                            elif op == "mod":
                                res = builder.srem(a, b, name=dest)
                            local_map[dest] = res
                        elif op == "ret":
                            if args:
                                v = args[0]
                                val = local_map.get(v, None)
                                if val is None:
                                    try:
                                        val = llir.Constant(int_t, int(v))
                                    except Exception:
                                        val = llir.Constant(int_t, 0)
                                builder.ret(val)
                            else:
                                builder.ret_void()
                        elif op == "call":
                            # call by name
                            fname_called = args[0]
                            n_args = int(args[1]) if len(args) > 1 else 0
                            called = func_map.get(fname_called)
                            if called:
                                _, llcalled = called
                                call_args = []
                                for i in range(n_args):
                                    argn = instr.args[2 + i] if len(instr.args) > 2 + i else None
                                    if argn:
                                        av = local_map.get(argn)
                                        if av is None:
                                            try:
                                                av = llir.Constant(int_t, int(argn))
                                            except Exception:
                                                av = llir.Constant(int_t, 0)
                                        call_args.append(av)
                                callres = builder.call(llcalled, call_args, name=dest or "")
                                if dest:
                                    local_map[dest] = callres
                        # other ops ignored in this tiny backend
                    except Exception as e:
                        # capture but continue
                        self.errors.append(IRGenError(IRGenErrorCode.Other, f"LLVM lowering error: {e}"))
                        continue

        # finalize module -> bitcode
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        # compile module to bitcode (bytes)
        bc = str(module).encode("utf-8")
        return module, bc


# ---------- Example usage (small test) ----------
if __name__ == "__main__":
    # sample AST using BinaryOp, FnCall, etc.
    sample_ast = [
        # function def: def add(x:int, y:int) -> int: return x + y
        {
            "Function": "def",
            "identifier": "add",
            "params": [("Param", "int", "x"), ("Param", "int", "y")],
            "return type": "int",
            "body": {"type": "Statements", "block": [
                {"type": "jump statement", "keyword": "return", "args":
                    {"type": "BinaryOp", "op": "+",
                     "left": {"type":"Identifier","name":"x"},
                     "right": {"type":"Identifier","name":"y"}}}
            ]}
        },
        # function call at top level: add(1,2)
        {"type": "fn call", "args": [("identifier","add"), {"type":"Literal","value":"1","literal_type":"int"}, {"type":"Literal","value":"2","literal_type":"int"}]}
    ]

    # fake symbol table (global scope)
    global_sym = {}
    # register add in the global symbol table so calls look it up
    # mimic Symbol with .datatype and .info.node as used by the generator
    class FakeSym:
        def __init__(self, name, kind, datatype, info):
            self.name = name
            self.kind = kind
            self.datatype = datatype
            self.info = info

    global_sym["add"] = FakeSym("add", "func", "int", {"node": sample_ast[0]})

    gen = IRGenerator(sample_ast, symbol_table=[global_sym])
    fns, errs = gen.generate()
    print("=== TAC ===")
    print(gen.to_text())
    print("=== ERRORS ===")
    for e in errs:
        print(e)

    if HAS_LLVM:
        mod_and_bc = gen.to_llvmlite_module()
        if mod_and_bc:
            mod, bc = mod_and_bc
            print("--- LLVM IR ---")
            print(mod)
        else:
            print("LLVM backend produced no module.")
    else:
        print("llvmlite not installed; skipping LLVM backend demo.")
