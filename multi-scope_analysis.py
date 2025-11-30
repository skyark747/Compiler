import re
from typing import List, Tuple, Any

# operator precedence and associativity
# higher number = higher precedence
OP_INFO = {
    '||': (1, 'left'),
    '&&': (2, 'left'),
    '|':  (3, 'left'),
    '^':  (4, 'left'),
    '&':  (5, 'left'),
    '==': (6, 'left'), '!=': (6, 'left'),
    '<':  (7, 'left'), '<=': (7, 'left'), '>': (7, 'left'), '>=': (7, 'left'),
    '<<': (8, 'left'), '>>': (8, 'left'),
    '+':  (9, 'left'), '-':  (9, 'left'),
    '*':  (10, 'left'), '/': (10, 'left'), '%': (10, 'left'),
    '**': (11, 'right'),
    # assignment-like operators (treated as binary, lowest precedence)
    '=': (0, 'right'), '+=': (0, 'right'), '-=': (0, 'right'), '*=': (0, 'right'), '/=': (0, 'right'),
}

# token regex
_token_re = re.compile(r'''
    (?P<WS>\s+)|
    (?P<NUMBER>\d+\.\d+|\d+)|
    (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|
    (?P<OP>\|\||&&|==|!=|<=|>=|<<|>>|\*\*|\+=|-=|\*=|/=|\+=|-=|\^|\||&|\+|-|\*|/|%|=|<|>|\(|\)|,)|
    (?P<STRING>"(?:\\.|[^"\\])*")
''', re.VERBOSE)


def tokenize_expr(s: str) -> List[Tuple[str,str]]:
    tokens = []
    pos = 0
    while pos < len(s):
        m = _token_re.match(s, pos)
        if not m:
            # unknown single char -> treat as token
            tokens.append(('OP', s[pos]))
            pos += 1
            continue
        kind = m.lastgroup
        val = m.group(kind)
        pos = m.end()
        if kind == 'WS':
            continue
        if kind == 'NUMBER':
            tokens.append(('NUMBER', val))
        elif kind == 'IDENT':
            tokens.append(('IDENT', val))
        elif kind == 'STRING':
            tokens.append(('STRING', val))
        else:
            tokens.append(('OP', val))
    return tokens


# Helper to build AST nodes
def make_ident(name: str) -> dict:
    return {'type':'Identifier', 'name':name}

def make_literal(tok_type: str, tok_val: str) -> dict:
    if tok_type == 'NUMBER':
        return {'type':'Literal', 'value':tok_val, 'literal_type': ('float' if '.' in tok_val else 'int')}
    if tok_type == 'STRING':
        return {'type':'Literal', 'value':tok_val, 'literal_type':'string'}
    return {'type':'Literal', 'value':tok_val}


def shunting_yard_to_ast(tokens: List[Tuple[str,str]]) -> Any:
    """
    Convert token list to AST using shunting-yard algorithm producing BinaryOp/UnaryOp nodes.
    """
    output_stack = []
    op_stack = []

    def push_op(op):
        # pop operators with higher precedence
        while op_stack:
            top = op_stack[-1]
            if top == '(':
                break
            if top not in OP_INFO:
                break
            top_prec, top_assoc = OP_INFO[top]
            op_prec, op_assoc = OP_INFO.get(op, (0,'left'))
            if (top_prec > op_prec) or (top_prec == op_prec and op_assoc == 'left'):
                op_stack.pop()
                apply_top_operator(top)
                continue
            break
        op_stack.append(op)

    def apply_top_operator(op):
        # unary handling for some operators like unary -, +
        if op in ('+', '-') and len(output_stack) >= 1:
            # ambiguous: need to detect unary vs binary; this simple approach assumes unary handled earlier
            pass
        # pop right and left
        if op == '()':
            # function call handled separately
            return
        if op in OP_INFO or op in ('=','+=','-=','*=','/='):
            if len(output_stack) < 2:
                # malformed expression
                return
            right = output_stack.pop()
            left = output_stack.pop()
            output_stack.append({'type':'BinaryOp', 'op':op, 'left':left, 'right':right})
        else:
            # unknown operator
            if len(output_stack) >= 1:
                operand = output_stack.pop()
                output_stack.append({'type':'UnaryOp', 'op':op, 'operand':operand})

    i = 0
    n = len(tokens)
    # to support unary operators, track previous token type
    prev_token_type = 'START'
    while i < n:
        tk_type, tk_val = tokens[i]
        if tk_type == 'NUMBER' or tk_type == 'STRING':
            output_stack.append(make_literal(tk_type, tk_val))
            prev_token_type = 'OPERAND'
            i += 1
            continue
        if tk_type == 'IDENT':
            # could be function call if next token is '('
            if i+1 < n and tokens[i+1][0] == 'OP' and tokens[i+1][1] == '(':
                # parse function call arguments
                func_name = tk_val
                # find matching ')'
                j = i+2
                depth = 1
                args_tokens = []
                current_arg = []
                while j < n and depth>0:
                    ttype, tval = tokens[j]
                    if ttype=='OP' and tval=='(':
                        depth += 1
                        current_arg.append((ttype,tval))
                    elif ttype=='OP' and tval==')':
                        depth -= 1
                        if depth==0:
                            if current_arg:
                                args_tokens.append(current_arg)
                            break
                        else:
                            current_arg.append((ttype,tval))
                    elif ttype=='OP' and tval==',' and depth==1:
                        args_tokens.append(current_arg)
                        current_arg = []
                    else:
                        current_arg.append((ttype,tval))
                    j += 1
                # recursively parse each arg tokens into AST nodes
                args_nodes = []
                for arg_toks in args_tokens:
                    if not arg_toks:
                        continue
                    args_nodes.append(shunting_yard_to_ast(arg_toks))
                output_stack.append({'type':'FnCall','name':func_name,'args':args_nodes})
                prev_token_type = 'OPERAND'
                i = j+1
                continue
            else:
                output_stack.append(make_ident(tk_val))
                prev_token_type = 'OPERAND'
                i += 1
                continue
        if tk_type == 'OP':
            val = tk_val
            if val == '(':
                op_stack.append('(')
                prev_token_type = 'OP'
                i += 1
                continue
            if val == ')':
                # pop until '('
                while op_stack and op_stack[-1] != '(':
                    apply_top_operator(op_stack.pop())
                if op_stack and op_stack[-1] == '(':
                    op_stack.pop()
                prev_token_type = 'OPERAND'
                i += 1
                continue

            # Handle unary + and - if previous token was operator or start
            if val in ('+', '-') and prev_token_type in ('START','OP'):
                # treat unary as special token 'u+' or 'u-'
                # For simplicity represent unary as 'u+' 'u-'
                op = 'u'+val
                # apply immediately (unary has high precedence)
                # parse the next operand
                # We'll push unary operator and expect operand
                # For simplicity, push as operator and let apply_top_operator handle unary
                op_stack.append(op)
                prev_token_type = 'OP'
                i += 1
                continue

            # normal binary operator
            if val not in OP_INFO:
                # unknown operator, push as-is
                push_op(val)
            else:
                push_op(val)
            prev_token_type = 'OP'
            i += 1
            continue
        # fallback
        i += 1

    # drain operator stack
    while op_stack:
        op = op_stack.pop()
        if op == '(':
            continue
        apply_top_operator(op)

    # if output_stack has a single element, return it; if multiple, wrap
    if len(output_stack) == 1:
        return output_stack[0]
    return {'type':'ExpressionSequence','items': output_stack}


def parse_expression_from_str(s: str) -> dict:
    toks = tokenize_expr(s)
    ast = shunting_yard_to_ast(toks)
    return ast

# Quick test when run as script
if __name__ == '__main__':
    tests = [
        'a + b * (c - 2)',
        'x == y && z != 0',
        'foo(1, x+2, bar(y))',
        '-a + 3',
        'a += b',
    ]
    for t in tests:
        print(t)
        print(parse_expression_from_str(t))
        print('---')
