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
# test_from_source.py
# Purpose: build AST for the sample source, run TypeChecker and IRGenerator, print results.
import traceback
import pprint

# --- imports from your project files ---
from Type_Checker import TypeChecker, TypeChkError
from ir_generator import IRGenerator, IRGenError

# FakeSym shim (ir_generator.py might only define FakeSym inside __main__)
try:
    from ir_generator import FakeSym
except Exception:
    class FakeSym:
        def __init__(self, name, kind, datatype, info=None):
            self.name = name
            self.kind = kind
            self.datatype = datatype
            self.info = info or {}

# --- the exact source you gave (kept here for clarity) ---
SOURCE = """
def int main(){
    print(125648);
    if(z==b && f==c) {
        print(n);
    }
}
"""

# --- Minimal "parser" for exactly this source ---
# We do not attempt to implement a full parser. Instead, this function
# returns an AST (dictionary/list shapes) matching the format used by
# your TypeChecker and IRGenerator for the provided source.
def build_ast_for_sample():
    # Function node for: def int main() { ... }
    main_fn = {
        "Function": "def",
        "identifier": "main",
        "params": [],
        "return type": "int",
        "body": {
            "type": "Statements",
            "block": [
                # print(125648);
                {
                    "type": "fn call",
                    "args": [
                        ("identifier", "print"),
                        {
                            "type": "Literal",
                            "value": "125648",
                            "literal_type": "int"
                        }
                    ]
                },
                # if (z == b && f == c) { print(n); }
                {
                    "type": "conditional statement",
                    "args": {
                        "type": "BinaryOp",
                        "op": "&&",
                        "left": {
                            "type": "BinaryOp",
                            "op": "==",
                            "left": {"type": "Identifier", "name": "z"},
                            "right": {"type": "Identifier", "name": "b"}
                        },
                        "right": {
                            "type": "BinaryOp",
                            "op": "==",
                            "left": {"type": "Identifier", "name": "f"},
                            "right": {"type": "Identifier", "name": "c"}
                        }
                    },
                    "body": {
                        "type": "Statements",
                        "block": [
                            {
                                "type": "fn call",
                                "args": [
                                    ("identifier", "print"),
                                    {"type": "Identifier", "name": "n"}
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    }
    # The module AST is a list of top-level nodes (functions + top-level statements)
    return [main_fn]

# --- Build a symbol table compatible with your tools ---
# Put functions and referenced variable names in the global scope.
def build_symbol_table():
    global_sym = {}
    global_sym["main"] = FakeSym("main", "func", "int", info={"node": None})
    global_sym["print"] = FakeSym("print", "func", "void", info={})
    # Variables referenced in the condition / print arg
    global_sym["z"] = FakeSym("z", "var", "int")
    global_sym["b"] = FakeSym("b", "var", "int")
    global_sym["f"] = FakeSym("f", "var", "int")
    global_sym["c"] = FakeSym("c", "var", "int")
    global_sym["n"] = FakeSym("n", "var", "int")
    # The TypeChecker/IRGenerator often accept either a single dict or a list of dicts.
    return [global_sym]

# --- Test runner that prints outputs and catches errors ---
def run_ast_test(name, ast, symtab):
    print("="*72)
    print("TEST:", name)
    print("- Type checking:")
    try:
        tc = TypeChecker(symtab.copy(), ast)
        errors, warnings = tc.run()
    except Exception:
        print("  TypeChecker raised an exception:")
        traceback.print_exc()
        errors, warnings = [], []

    if not errors:
        print("  No type errors.")
    else:
        print(f"  Found {len(errors)} type error(s):")
        for e in errors:
            # TypeChkError entries are typically tuples (code, message, node)
            try:
                code, msg, node = e
                name = getattr(code, "name", str(code))
                print(f"   - {name}: {msg}")
            except Exception:
                print("   - (unprintable error):", repr(e))

    if warnings:
        print("  Warnings:")
        for w in warnings:
            print("   -", w)

    print("\n- IR generation:")
    try:
        irg = IRGenerator(ast, symbol_table=symtab)
        functions, ir_errors = irg.generate()
        # print textual IR if produced
        text = irg.to_text()
        if text:
            print(text)
        else:
            print("  (no IR emitted)")
        if ir_errors:
            print("  IR errors returned by generate():")
            for er in ir_errors:
                try:
                    print(f"   - {er.code.name}: {er.message}")
                except Exception:
                    print("   -", repr(er))
    except Exception:
        print("  IRGenerator raised an exception during generate():")
        traceback.print_exc()
        # Try to identify the top-level node that caused the crash
        print("\n  Attempting one-by-one top-level node gen to find offending node...")
        try:
            irg2 = IRGenerator([], symbol_table=symtab)
            for i, node in enumerate(ast):
                try:
                    # call private method to exercise the same generation path
                    if isinstance(node, dict):
                        irg2._gen_node(node)
                    else:
                        # Non-dict top-level nodes may be statements lists; attempt to call generate on slice
                        irg_temp = IRGenerator([node], symbol_table=symtab)
                        irg_temp.generate()
                except Exception:
                    print(f"\n  Exception while processing top-level AST node index {i}:")
                    pprint.pprint(node)
                    print("  Traceback:")
                    traceback.print_exc()
                    break
            else:
                print("  One-by-one pass completed without reproducing the crash.")
        except Exception:
            print("  One-by-one isolation also failed:")
            traceback.print_exc()

    print("\n")

# --- main entrypoint ---
if __name__ == "__main__":
    ast = build_ast_for_sample()
    # attach function AST into its symbol info if needed by IRGenerator/TypeChecker
    # (some modules expect FakeSym.info['node'] to hold the function node)
    if ast and isinstance(ast[0], dict) and ast[0].get("Function") == "def":
        try:
            symtab = build_symbol_table()
            # put actual function node into the symbol entry
            symtab[0]["main"].info["node"] = ast[0]
        except Exception:
            symtab = build_symbol_table()
    else:
        symtab = build_symbol_table()

    run_ast_test("sample main() with && conditional", ast, symtab)
