import json
from scope_analysis import ScopeAnalyzer

with open(".txt", "r") as infile:
    ast = json.load(infile)

sa = ScopeAnalyzer()
globals_, errors, warnings = sa.analyze_program(ast)

print("\n=== Scope Analysis Results ===")
print("Global Symbols:")
for name, sym in globals_.items():
    print(f"  {name}: {sym}")

print("\nErrors:")
for err in errors:
    print(f"  {err[0].name} → {err[1]}")

print("\nWarnings:")
for warn in warnings:
   print(f"  {warn[0].name} → {warn[1]}")