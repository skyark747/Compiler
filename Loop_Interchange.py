# (This is the same code I executed for you in the session.)
# It builds a small double-loop AST, emits LLVM-like IR for the original nested loops,
# then performs loop interchange and emits LLVM-like IR for the interchanged loops.
# See the notebook output for the printed IR.

def emit_alloca(var):
    return f"  %{var} = alloca i32, align 4"

def emit_store(var, val):
    return f"  store i32 {val}, i32* %{var}, align 4"

def emit_load(var, to):
    return f"  %{to} = load i32, i32* %{var}, align 4"

def emit_icmp_slt(lhs_reg, rhs_val, to):
    return f"  %{to} = icmp slt i32 %{lhs_reg}, {rhs_val}"

def emit_add(lhs_reg, addend, to):
    return f"  %{to} = add i32 %{lhs_reg}, {addend}"

def llvm_for(loop, labels_prefix):
    init, cond, update = loop["args"]
    iv = init["identifier"]
    bound = cond["value"]
    lines = []
    lines.append(emit_alloca(iv))
    lines.append(emit_store(iv, init.get("value", 0)))
    cond_lbl = f"{labels_prefix}.cond"
    body_lbl = f"{labels_prefix}.body"
    update_lbl = f"{labels_prefix}.update"
    exit_lbl = f"{labels_prefix}.exit"
    lines.append(f"  br label %{cond_lbl}")
    lines.append(f"{cond_lbl}:")
    lines.append(emit_load(iv, f"{iv}.val"))
    lines.append(emit_icmp_slt(f"{iv}.val", bound, f"{iv}.cmp"))
    lines.append(f"  br i1 %{iv}.cmp, label %{body_lbl}, label %{exit_lbl}")
    lines.append(f"{body_lbl}:")
    for stmt in loop["body"]["block"]:
        if stmt["type"] == "FunctionCall":
            args = stmt["args"]
            loads = []
            for a in args:
                if isinstance(a, str):
                    lines.append(emit_load(a, f"{a}.val")) 
                    loads.append(f"%{a}.val")
                else:
                    loads.append(str(a))
            lines.append(f"  call void @print({', '.join('i32 ' + x for x in loads)})")
        elif stmt["type"] == "iteration":
            nested_lines, nested_iv = llvm_for(stmt, labels_prefix + ".nested")
            lines.extend(nested_lines)
    lines.append(f"  br label %{update_lbl}")
    lines.append(f"{update_lbl}:")
    lines.append(emit_load(iv, f"{iv}.val2"))
    lines.append(emit_add(f"{iv}.val2", 1, f"{iv}.inc"))
    lines.append(emit_store(iv, f"%{iv}.inc"))
    lines.append(f"  br label %{cond_lbl}")
    lines.append(f"{exit_lbl}:")
    return lines, iv

# build a simple AST with outer loop i in [0,3), inner loop j in [0,4),
# body: print(i,j)
ast_double_loop = {
    "identifier": "main",
    "body": {
        "block": [
            {
                "type": "iteration",
                "args": [
                    {"type": "declaration", "identifier": "i", "value": 0},
                    {"type": "OperatorExpression", "identifier": "i", "operator": "<", "value": 3},
                    {"type": "OperatorExpression", "identifier": "i", "operator": "=", "value": {"type":"OperatorExpression","identifier":"i","operator":"+","value":1}},
                ],
                "body": {
                    "block": [
                        {
                            "type": "iteration",
                            "args": [
                                {"type": "declaration", "identifier": "j", "value": 0},
                                {"type": "OperatorExpression", "identifier": "j", "operator": "<", "value": 4},
                                {"type": "OperatorExpression", "identifier": "j", "operator": "=", "value": {"type":"OperatorExpression","identifier":"j","operator":"+","value":1}},
                            ],
                            "body": {
                                "block": [
                                    {"type":"FunctionCall", "keyword":"print", "args":["i","j"]}
                                ]
                            }
                        }
                    ]
                }
            }
        ]
    }
}

def is_nested_loop(loop_node):
    blk = loop_node["body"]["block"]
    if len(blk) == 1 and blk[0]["type"] == "iteration":
        return True
    return False

def interchange_loops(loop_node):
    outer = loop_node
    inner = outer["body"]["block"][0]
    new_outer = {
        "type": "iteration",
        "args": inner["args"],
        "body": {
            "block": [
                {
                    "type":"iteration",
                    "args": outer["args"],
                    "body": inner["body"]
                }
            ]
        }
    }
    return new_outer

def emit_function_for_ast(ast):
    lines = ["define i32 @main() {"]
    top_block = ast["body"]["block"]
    for stmt in top_block:
        if stmt["type"] == "iteration":
            lines.append("  ; --- original nested loops ---")
            nested_lines, _ = llvm_for(stmt, "outer")
            lines.extend(nested_lines)
    lines.append("  ret i32 0")
    lines.append("}")
    return "\n".join(lines)

def emit_function_for_ast_interchanged(ast):
    lines = ["define i32 @main() {"]
    top_block = ast["body"]["block"]
    for stmt in top_block:
        if stmt["type"] == "iteration" and is_nested_loop(stmt):
            swapped = interchange_loops(stmt)
            lines.append("  ; --- after loop interchange (outer and inner swapped) ---")
            swapped_lines, _ = llvm_for(swapped, "outer_swapped")
            lines.extend(swapped_lines)
    lines.append("  ret i32 0")
    lines.append("}")
    return "\n".join(lines)

original_llvm = emit_function_for_ast(ast_double_loop)
interchanged_llvm = emit_function_for_ast_interchanged(ast_double_loop)

print("=== ORIGINAL LLVM-LIKE IR ===\n")
print(original_llvm)
print("\n\n=== INTERCHANGED LLVM-LIKE IR ===\n")
print(interchanged_llvm)
