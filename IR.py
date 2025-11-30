import json

class TACGenerator:
    def __init__(self):
        self.temp_counter = 1
        self.label_counter = 1
        self.code = []

    # ----------------------------
    # Helpers
    # ----------------------------
    def new_temp(self):
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self, base="L"):
        l = f"{base}{self.label_counter}"
        self.label_counter += 1
        return l

    # ----------------------------
    # Main entry
    # ----------------------------
    def generate(self, ast):
        for func in ast:
            self.emit_function(func)
        return self.code

    # ----------------------------
    # Functions
    # ----------------------------
    def emit_function(self, node):
        fn = node["identifier"]
        self.code.append(f"\n# Function {fn}")
        self.code.append(f"{fn}:")

        self.emit_statements(node["body"])

        self.code.append(f"# End {fn}")

    # ----------------------------
    # Statement Block
    # ----------------------------
    def emit_statements(self, node):
        for stmt in node["block"]:
            self.emit_statement(stmt)

    def emit_statement(self, stmt):
        t = stmt["type"]

        if t == "iteration":
            self.emit_for(stmt)
        elif t == "OperatorExpression":
            self.emit_operator(stmt)
        elif t == "FunctionCall":
            self.emit_function_call(stmt)
        elif t == "declaration":
            self.emit_declaration(stmt)
        else:
            # If needed add more types here
            pass

    # Operator Expression (e.g., i += 1, i < 10)
    def emit_operator(self, node):
        ident = node["identifier"]
        op = node["operator"]
        value = node["value"]

        # literal
        if isinstance(value, int):
            val = value
        else:
            val = self.emit_expression(value)

        self.code.append(f"{ident} {op} {val}")

    # Expression Handling
    def emit_expression(self, node):
        if isinstance(node, int):
            return node

        if isinstance(node, str):
            return node  # identifier

        t = node['type']

        if t == "OperatorExpression":
            return self.emit_binary(node)

        return "<expr>"

    def emit_binary(self, node):
        left = node["identifier"]
        op = node["operator"]
        right = node["value"]

        if isinstance(right, dict):
            right = self.emit_expression(right)

        temp = self.new_temp()
        self.code.append(f"{temp} = {left} {op} {right}")
        return temp

    # Declaration (int i = 0)
    def emit_declaration(self, node):
        name = node["identifier"]
        value = node.get("value", None)
        if value is None:
            self.code.append(f"{name} = 0")
        else:
            self.code.append(f"{name} = {value}")

    # Function Call (print(...))
    def emit_function_call(self, node):
        args = ", ".join(map(str, node["args"]))
        self.code.append(f"call {node['keyword']} {args}")

    # For Loop TAC
    def emit_for(self, node):
        init = node["args"][0]      
        cond = node["args"][1]      
        update = node["args"][2]    

        start_label = self.new_label("L")
        end_label = self.new_label("L")

        # initialization
        self.emit_statement(init)

        # start label
        self.code.append(f"{start_label}:")

        # condition
        cond_temp = self.emit_expression(cond)
        self.code.append(f"ifnot {cond_temp} goto {end_label}")

        # body
        self.emit_statements(node["body"])

        # update
        self.emit_operator(update)

        # loop back
        self.code.append(f"goto {start_label}")

        # exit label
        self.code.append(f"{end_label}:")

with open("ast.txt", "r") as infile:
    ast = json.load(infile)

gen = TACGenerator()
tac = gen.generate(ast)

for line in tac:
    print(line)