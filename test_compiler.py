# import json
# from scope_analysis import ScopeAnalyzer

# with open(".txt", "r") as infile:
#     ast = json.load(infile)

# sa = ScopeAnalyzer()
# globals_, errors, warnings = sa.analyze_program(ast)

# print("\n=== Scope Analysis Results ===")
# print("Global Symbols:")
# for name, sym in globals_.items():
#     print(f"  {name}: {sym}")

# print("\nErrors:")
# for err in errors:
#     print(f"  {err[0].name} → {err[1]}")

# print("\nWarnings:")
# for warn in warnings:
#    print(f"  {warn[0].name} → {warn[1]}")

# driver_typecheck.py
# import parser
# from scope_analysis import ScopeAnalyzer
# from Type_Checker import TypeChecker

# ast = parser.parse_program(parser.tokens)   # or load AST from file

# sa = ScopeAnalyzer()
# globals_tbl, scope_errors, scope_warnings = sa.analyze_program(ast)

# tc = TypeChecker(ast, scope_analyzer=sa)
# type_errors = tc.type_check()

# print("Scope errors:", scope_errors)
# print("Scope warnings:", scope_warnings)
# print("Type errors:")
# for e in type_errors:
#     print(f"- {e.kind.name}: {e.message}")


# test_compiler.py
# Usage: python test_compiler.py
from Type_Checker import TypeChecker, SimpleSym, TypeChkError
# test_compiler.py
from Type_Checker import TypeChecker, SimpleSym, TypeChkError
from ir_generator import IRGenerator, IRGenError

# FakeSym shim (ir_generator.py defines it only inside __main__)
try:
    from ir_generator import FakeSym
except ImportError:
    class FakeSym:
        def __init__(self, name, kind, datatype, info=None):
            self.name = name
            self.kind = kind
            self.datatype = datatype
            self.info = info or {}

# Note: ir_generator.py defines a FakeSym inside __main__ in the file shown, but if it's not exported,
# we'll create a tiny one here for the symbol table consumed by IRGenerator.

# If ir_generator.py did not expose FakeSym as a top-level, create compatible shim:
class FakeSymLocal:
    def __init__(self, name, kind, datatype, info=None):
        self.name = name
        self.kind = kind
        self.datatype = datatype
        self.info = info or {}

# Helper to run both type checker and IR generator
import traceback
import sys

def run_test(name: str, program_ast, symbol_table_list):
    print("="*70)
    print(f"TEST: {name}")
    print("- Type checking:")
    tc = TypeChecker(symbol_table_list.copy(), program_ast)
    try:
        errors, warnings = tc.run()
    except Exception as e:
        print("  TypeChecker raised exception:")
        traceback.print_exc()
        errors, warnings = [], []

    if not errors:
        print("  No type errors.")
    else:
        print(f"  Found {len(errors)} error(s):")
        for e in errors:
            # TypeChkError entries are (code, message, node)
            try:
                code, msg, node = e
                print(f"    - {code.name if hasattr(code,'name') else code}: {msg}")
            except Exception:
                print("   ", repr(e))

    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for w in warnings:
            print("    -", w)

    print("\n- IR generation:")
    irg = IRGenerator(program_ast, symbol_table=symbol_table_list)

    try:
        functions, ir_errors = irg.generate()
    except Exception as exc:
        # Generator crashed — best effort to locate problem
        print("  IRGenerator raised an exception during generate():")
        traceback.print_exc()

        # Try to re-run generate but process nodes one-by-one to locate offending node
        print("\n  Attempting one-by-one generation to find offending node...")
        try:
            # reset the generator state
            irg = IRGenerator(program_ast, symbol_table=symbol_table_list)
            for idx, node in enumerate(program_ast):
                try:
                    # Only process dict nodes (generator.generate() does that check too)
                    if isinstance(node, dict):
                        # call internal visitor on the node; wrap in try/except
                        irg._gen_node(node)   # note: private method but useful for debugging
                    else:
                        # fallback: call generate on the entire ast up to this point
                        pass
                except Exception as e_node:
                    print(f"\n  Exception while processing top-level AST node index {idx}:")
                    print("  Node repr:")
                    import pprint
                    pprint.pprint(node)
                    print("\n  Exception traceback:")
                    traceback.print_exc()
                    break
            else:
                print("  One-by-one pass completed without reproducing crash.")
        except Exception:
            print("  One-by-one pass also failed to isolate the problem.")
            traceback.print_exc()

        # print whatever IR errors were accumulated
        if irg.errors:
            print("\n  IR errors collected before crash:")
            for e in irg.errors:
                try:
                    print(f"    - {e.code.name}: {e.message}")
                except Exception:
                    print("    -", repr(e))

        print("\n  Generator internal state (sanity):")
        print("    functions:", list(irg.functions.keys()))
        print("    temp counter at:", getattr(irg, "_temp_counter", None))
        return  # bail out of this test

    # if no exception:
    text = irg.to_text()
    if text:
        print(text)
    else:
        print("  (no functions emitted)")

    if irg.errors:
        print("  IR errors:")
        for err in irg.errors:
            # err has .code (enum) and .message and .node typically
            try:
                print(f"    - {err.code.name}: {err.message}")
            except Exception:
                print("    -", repr(err))

    print("\n")


# -----------------------------
# Build a global symbol table (list-of-dicts outer->inner). Use SimpleSym / FakeSym shapes.
global_scope = {}

# Define a good function: add(x:int, y:int) -> int { return x + y; }
add_node = {
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
}

# Register add in global scope as a symbol (so calls are resolvable by TypeChecker & IRGenerator)
global_scope["add"] = FakeSymLocal("add", "func", "int", info={"node": add_node})

# Small good program: define add, then call it and print result.
good_program = [
    add_node,
    # top-level statements: t = add(1,2); print(t)
    {"type": "Statements", "block": [
        # local decl t:int = add(1,2)  (we model as assign)
        {"type": "assignment",
         "target": "t",
         "value": {"type": "FnCall", "name": "add", "args": [
             {"type":"Literal","value":"1","literal_type":"int"},
             {"type":"Literal","value":"2","literal_type":"int"}
         ]}},
        # print(t) using old-style `fn call` shape expected in your TypeChecker example
        {"type":"fn call", "args": [("identifier","print"), ("identifier","t")]},
    ]}
]

# Create symbol table with globals (some modules expect list-of-dicts)
symbol_table_for_good = [ {"add": global_scope["add"], "print": FakeSymLocal("print","func","void", info={})} ]

# -----------------------------
# Build a bad program that triggers several TypeChecker errors:
# - Call add with wrong types (string instead of int)
# - Assign string to int variable
# - If condition with non-bool
bad_program = [
    add_node,  # still present in global scope
    {"type": "Statements", "block": [
        # call add("hello", 2.0) -> param type mismatch
        {"type": "fn call", "args": [("identifier","add"),
                                     {"type":"Literal","value":'"hello"',"literal_type":"string"},
                                     {"type":"Literal","value":"2.0","literal_type":"float"}]},
        # declare a:int = "oops"  (assignment type mismatch)
        {"datatype": "int", "identifier": "a", "value": '"oops"'},
        # conditional with non-bool (a is int)
        {"type":"conditional statement", "args": {"type":"Identifier","name":"a"}, "body": {"type":"Statements","block":[]}},
        # return from top-level (return outside function)
        {"type":"jump statement", "keyword":"return", "args": {"type":"Literal","value":"0","literal_type":"int"}}
    ]}
]

symbol_table_for_bad = [ {"add": global_scope["add"], "print": FakeSymLocal("print","func","void", info={}), "a": FakeSymLocal("a","var","int", info={})} ]

# Run tests
run_test("Good program (should pass type checking, emit IR for add)", good_program, symbol_table_for_good)
run_test("Bad program (expected type errors and some IR emission)", bad_program, symbol_table_for_bad)

# Optional: add more targeted tests below:
# - function missing return for non-void
missing_ret_node = {
    "Function":"def","identifier":"badret","params":[("Param","int","x")],"return type":"int",
    "body": {"type":"Statements","block":[
        # no return here
        {"type":"assignment","target":{"type":"Identifier","name":"y"},"value":{"type":"Literal","value":"1","literal_type":"int"}}
    ]}
}
run_test("Function missing return (should report ReturnStmtNotFound)", [missing_ret_node], [{"badret": FakeSymLocal("badret","func","int", info={"node": missing_ret_node})}])

