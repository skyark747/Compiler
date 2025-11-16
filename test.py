from scope_analysis import ScopeAnalyzer
from Type_Checker import TypeChecker
import parser

ast = parser.parse_program(parser.tokens)  # or however you get AST

sa = ScopeAnalyzer()
globals_tbl, sa_errors, sa_warnings = sa.analyze_program(ast)

tc = TypeChecker(ast, scope_analyzer=sa)
type_errors = tc.type_check()

print("Scope errors:", sa_errors)
print("Scope warnings:", sa_warnings)
print("\nType errors:")
for e in type_errors:
    print(f"- {e.kind.name}: {e.message}")

# ast = [
#     {
#         "Function": "def",
#         "identifier": "main",
#         "params": [],
#         "body": {
#             "type": "Statements",
#             "block": [
#                 {"datatype": "int", "identifier": "x", "value": "5"},
#                 {"type": "OperatorExpression", "identifier": "y", "value": "10"},  # y undeclared
#                 {"type": "jump statement", "keyword": "return", "args": None}
#             ]
#         }
#     }
# ]

# sa = ScopeAnalyzer()
# globals_, errors = sa.analyze_program(ast)

# print("\n=== Scope Analysis Results ===")
# print("Global Symbols:")
# for name, sym in globals_.items():
#     print(f"  {name}: {sym}")

# print("\nErrors:")
# for err in errors:
#     print(f"  {err[0].name} → {err[1]}")

# #print("\nWarnings:")
# #for warn in warnings:
# #    print(f"  {warn[0].name} → {warn[1]}")