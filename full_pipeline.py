#!/usr/bin/env python3
"""
full_pipeline.py

- Usage: python full_pipeline.py source.txt
- Expects in same folder:
    - lexer.cpp   (C++ lexer that writes lexer_output.txt when executed with source string)
    - parser.py   (the parser you provided; must expose parse_tokens_return(tokens) OR parse_program(tokens))
    - scope_analyzer.py
"""

import subprocess
import sys
import json
import os
from pathlib import Path
import importlib.util

SCRIPT_DIR = Path(__file__).resolve().parent
LEXER_CPP = SCRIPT_DIR / "lexer.cpp"
LEXER_EXE = SCRIPT_DIR / ("lexer.exe" if os.name == "nt" else "lexer.out")
LEXER_OUTPUT = SCRIPT_DIR / "lexer_output.txt"
PARSER_PATH = SCRIPT_DIR / "parser.py"
SCOPE_PATH = SCRIPT_DIR / "scope_analyzer.py"

# ---------- utilities -------------------------------------------------------

def import_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def compile_lexer():
    if not LEXER_CPP.exists():
        raise FileNotFoundError(f"lexer.cpp not found at {LEXER_CPP}")
    # compile
    cmd = ["g++", str(LEXER_CPP), "-o", str(LEXER_EXE)]
    print("Compiling lexer:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("Lexer compiled ->", LEXER_EXE)

def run_lexer_on_source(source_text: str):
    if not LEXER_EXE.exists():
        raise FileNotFoundError(f"Lexer executable not found at {LEXER_EXE}. Compile step likely failed.")
    # run lexer executable with source string as single arg (this mirrors your prior flow)
    cmd = [str(LEXER_EXE), source_text]
    print("Running lexer...")
    subprocess.run(cmd, check=True)
    if not LEXER_OUTPUT.exists():
        raise FileNotFoundError(f"Lexer did not produce expected {LEXER_OUTPUT}")
    print("Lexer wrote", LEXER_OUTPUT)
    # read lines
    with open(LEXER_OUTPUT, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    return lines

def decode_lexer_line(line: str):
    """
    Convert token strings like:
      T_IDENTIFIER(main)  -> ('T_IDENTIFIER', 'main')
      T_NUMLIT(5)         -> ('T_NUMLIT', '5')
      T_INT               -> ('T_INT', 'T_INT')   (no payload)
      'T_ARITHOP(=)' may appear with quotes; strip surrounding quotes
    """
    s = line.strip()
    # remove surrounding quotes if present
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1]
    # handle form TOKEN(payload)
    if "(" in s and s.endswith(")"):
        tok, rest = s.split("(", 1)
        payload = rest[:-1]  # remove trailing ')'
        return tok, payload
    # fallback: single token type, return token as both type and value
    return s, s

def lexer_lines_to_tokens(lines):
    tokens = []
    for ln in lines:
        tok, val = decode_lexer_line(ln)
        tokens.append((tok, val))
    return tokens

# ---------- high-level pipeline --------------------------------------------

def parse_tokens_with_parser_module(parser_mod, tokens):
    """
    Try a few possible parser entrypoints in order:
     - parse_tokens_return(tokens)
     - parse_program(tokens)  (common)
     - parse_tokens() or parse() (less likely — not used here)
    Raise RuntimeError with helpful message if none found.
    """
    if hasattr(parser_mod, "parse_tokens_return"):
        print("Using parser.parse_tokens_return")
        return parser_mod.parse_tokens_return(tokens)
    if hasattr(parser_mod, "parse_program"):
        print("Using parser.parse_program")
        # some implementations expect tokens of different shape; try to call and return result if any
        res = parser_mod.parse_program(tokens)
        return res
    # some parser implementations may expose a function that consumes Tokenizer.Tokens or similar
    # try common alternatives:
    if hasattr(parser_mod, "parse_tokens"):
        print("Using parser.parse_tokens")
        return parser_mod.parse_tokens(tokens)
    raise RuntimeError("Parser module does not expose parse_tokens_return or parse_program. "
                       "Please adapt parser.py to provide a function that returns the AST for given tokens.")

def run_full_pipeline(source_path: str):
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    source_text = source_path.read_text(encoding="utf-8")
    print("Source loaded (len {})".format(len(source_text)))

    # 1) compile lexer
    compile_lexer()

    # 2) run lexer
    lexer_lines = run_lexer_on_source(source_text)
    print("Raw lexer lines sample:", lexer_lines[:20])

    # 3) decode lines into token tuples
    tokens = lexer_lines_to_tokens(lexer_lines)
    print("Decoded tokens (sample):", tokens[:30])

    # write decoded tokens for debugging
    with open("lexer_output_decoded.json", "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

    # 4) import parser module
    if not PARSER_PATH.exists():
        raise FileNotFoundError(f"parser.py not found at {PARSER_PATH}")
    print("Importing parser module from", PARSER_PATH)
    parser_mod = import_module_from_path("user_parser", PARSER_PATH)

    # 5) convert tokens into the shape expected by parser if parser provides helper(s)
    # Some parsers expect Tokenizer.Tokens objects (see earlier pipeline). If parser exposes a helper
    # named 'get_tokenzizer' or 'get_tokenizer_from_lines', attempt to call it.
    # Otherwise assume tokens list of (TYPE,VALUE) is acceptable.
    try:
        tokenz = tokens
        if hasattr(parser_mod, "get_tokenzizer"):
            print("Using parser.get_tokenzizer to convert lexer lines -> tokens")
            tokenz = parser_mod.get_tokenzizer([ln for ln in lexer_lines])
        elif hasattr(parser_mod, "Tokenizer") and hasattr(parser_mod.Tokenizer, "Tokens"):
            try:
                tokenz = parser_mod.Tokenizer.Tokens([ln for ln in lexer_lines]).get_tokenizer()
                print("Converted using parser.Tokenizer.Tokens.get_tokenizer()")
            except Exception:
                # ignore and use raw tokens fallback
                pass
    except Exception as e:
        print("Warning: failed to run parser conversion helper; falling back to decoded tokens.", e)
        tokenz = tokens

    # 6) parse tokens -> AST
    print("Parsing tokens (this may raise if parser expects different token format)...")
    ast = parse_tokens_with_parser_module(parser_mod, tokenz)
    print("AST produced (type: {})".format(type(ast)))
    # dump AST to file
    with open("ast.json", "w", encoding="utf-8") as f:
        json.dump(ast, f, indent=2, default=str)

    # 7) import and run scope analyzer
    if not SCOPE_PATH.exists():
        raise FileNotFoundError(f"scope_analyzer.py not found at {SCOPE_PATH}")
    scope_mod = import_module_from_path("scope_analyzer_mod", SCOPE_PATH)
    if not hasattr(scope_mod, "ScopeAnalyzer"):
        raise RuntimeError("scope_analyzer.py does not expose ScopeAnalyzer class")

    analyzer = scope_mod.ScopeAnalyzer()
    print("Running scope analysis...")
    global_symbols, errors, warnings = analyzer.analyze_program(ast)

    # Print results
    print("\n--- Scope Analysis Summary ---")
    print("Global symbols:", list(global_symbols.keys()))
    print("Errors:")
    for e in errors:
        kind = e[0].name if hasattr(e[0], "name") else str(e[0])
        print(" -", kind, ":", e[1])
    print("Warnings:")
    for w in warnings:
        kind = w[0].name if hasattr(w[0], "name") else str(w[0])
        print(" -", kind, ":", w[1])

    # write scope report
    def serializable_errs(errs):
        out = []
        for e in errs:
            code = e[0].name if hasattr(e[0], "name") else str(e[0])
            out.append((code, e[1]))
        return out

    with open("scope_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "global_symbols": list(global_symbols.keys()),
            "errors": serializable_errs(errors),
            "warnings": serializable_errs(warnings)
        }, f, indent=2)

    print("\nOutputs written: ast.json, lexer_output_decoded.json, scope_report.json")
    return ast, (global_symbols, errors, warnings)


# ---------- main -----------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python full_pipeline.py <source.txt>")
        sys.exit(1)
    src = sys.argv[1]
    try:
        run_full_pipeline(src)
    except subprocess.CalledProcessError as e:
        print("External command failed:", e)
        sys.exit(2)
    except Exception as e:
        print("Error:", e)
        raise
