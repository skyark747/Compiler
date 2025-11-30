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
import parser
from scope_analysis import ScopeAnalyzer
from Type_Checker import TypeChecker

ast = parser.parse_program(parser.tokens)   # or load AST from file

sa = ScopeAnalyzer()
globals_tbl, scope_errors, scope_warnings = sa.analyze_program(ast)

tc = TypeChecker(ast, scope_analyzer=sa)
type_errors = tc.type_check()

print("Scope errors:", scope_errors)
print("Scope warnings:", scope_warnings)
print("Type errors:")
for e in type_errors:
    print(f"- {e.kind.name}: {e.message}")
