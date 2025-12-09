import re

with open('parser.py', 'r') as f:
    content = f.read()

# Replace patterns for float literal checks
patterns = [
    # Pattern 1: tokens[current_pos][0]=="T_FLOATLIT"
    (r'tokens\[current_pos\]\[0\]=="T_FLOATLIT"', 
     r'(tokens[current_pos][0]=="T_FLOATLIT" or tokens[current_pos][0]=="T_FLOATNLIT")'),
    
    # Pattern 2: in ["T_NUMLIT", "T_FLOATLIT"]
    (r'in \["T_NUMLIT", "T_FLOATLIT"\]',
     r'in ["T_NUMLIT", "T_FLOATLIT", "T_FLOATNLIT"]'),
     
    # Pattern 3: token_type=="T_FLOATLIT" in parse_digits
    (r'elif token_type=="T_FLOATLIT":',
     r'elif token_type=="T_FLOATLIT" or token_type=="T_FLOATNLIT":'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

with open('parser.py', 'w') as f:
    f.write(content)

print("Updated parser.py successfully")
