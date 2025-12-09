import json

class TACGenerator:
    def __init__(self):
        self.temp_counter = 1
        self.label_counter = 1
        self.code = []

    def new_temp(self):
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self, base="L"):
        l = f"{base}{self.label_counter}"
        self.label_counter += 1
        return l

    def generate(self, ast):
        for func in ast:
            self.emit_function(func)
        return self.code

    # def emit_function(self, node):
    #     fn = node["identifier"]
    #     self.code.append(f"{fn}:")
    #     self.emit_statements(node["body"])
    #     self.code.append(f"# End {fn}")

    def emit_function(self, node):
        fn = node["identifier"]
        
        if "params" in node:
            for p in node["params"]:
                self.code.append(f"param {p}")

        self.code.append(f"{fn}:")
        self.emit_statements(node["body"])
        self.code.append(f"# End {fn}")

    def emit_statements(self, node):
        for stmt in node["block"]:
            self.emit_statement(stmt)

    def emit_statement(self, stmt):
        t = stmt["type"]

        if t == "iteration":
            if stmt["keyword"] == "for":
                self.emit_for(stmt)
        elif t == "conditional statement":
            kw = stmt["keyword"]
            if kw == "while":
                self.emit_while(stmt)
            elif kw == "if":
                self.emit_if(stmt)
            elif kw == "else":
                self.emit_else(stmt)
        elif t == "OperatorExpression":
            self.emit_operator(stmt)
        elif t == "FunctionCall":
            self.emit_function_call(stmt)
        elif t == "declaration":
            self.emit_declaration(stmt)
        else:
            pass

    def emit_declaration(self, node):
        name = node["identifier"]
        value = node.get("value")

        if value is None:
            self.code.append(f"{name} = 0")
        else:
            val = self.emit_expression(value)
            self.code.append(f"{name} = {val}")

    def emit_operator(self, node):
        ident = node["identifier"]
        op = node["operator"]
        value = node["value"]

        val = self.emit_expression(value)
        self.code.append(f"{ident} {op} {val}")

    def emit_expression(self, node):
        if isinstance(node, int):
            return node

        if isinstance(node, str):
            return node

        if node["type"] == "OperatorExpression":
            op = node["operator"]

            if "identifier" in node and "value" in node:
                left = node["identifier"]
                right = self.emit_expression(node["value"])

            else:
                left = self.emit_expression(node["left"])
                right = self.emit_expression(node["right"])

            temp = self.new_temp()
            self.code.append(f"{temp} = {left} {op} {right}")
            return temp

        if node.get("type") == "FunctionCall":
            func_name = node["keyword"]
            args = ", ".join(map(str, node["args"]))
            temp = self.new_temp()
            self.code.append(f"{temp} = call {func_name}({args})")
            return temp

        return "<expr>"

    def emit_function_call(self, node):
        args = ", ".join(map(str, node["args"]))
        self.code.append(f"call {node['keyword']} {args}")

    def emit_for(self, node):
        init = node["args"][0]
        cond = node["args"][1]
        update = node["args"][2]

        start_label = self.new_label("L")
        end_label = self.new_label("L")

        self.emit_statement(init)

        self.code.append(f"{start_label}:")

        cond_temp = self.emit_expression(cond)
        self.code.append(f"ifnot {cond_temp} goto {end_label}")

        self.emit_statements(node["body"])

        self.emit_operator(update)

        self.code.append(f"goto {start_label}")

        self.code.append(f"{end_label}:")

    def emit_while(self, node):
        cond = node["args"]

        start_label = self.new_label("L")
        end_label = self.new_label("L")

        self.code.append(f"{start_label}:")

        cond_temp = self.emit_expression(cond)
        self.code.append(f"ifnot {cond_temp} goto {end_label}")

        self.emit_statements(node["body"])

        self.code.append(f"goto {start_label}")
        self.code.append(f"{end_label}:")

    def emit_if(self, node):
        cond = node["args"]
        false_label = self.new_label("L")

        cond_temp = self.emit_expression(cond)
        self.code.append(f"ifnot {cond_temp} goto {false_label}")

        self.emit_statements(node["body"])
        self.code.append(f"{false_label}:")

    def emit_else(self, node):
        self.emit_statements(node["body"])


with open("ast.txt", "r") as infile:
    ast = json.load(infile)

gen = TACGenerator()
tac = gen.generate(ast)

for line in tac:
    print(line)