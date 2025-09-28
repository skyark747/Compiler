import Tokenizer


Tokens=["T_FUNCTION","T_INT","T_IDENTIFIER(main)","T_PARENL","T_PARENR","T_BRACEL","T_INT","T_IDENTIFIER(n)","T_ASSIGNOP",
        "T_NUMLIT(29)","T_SEMICOLON","T_INT","T_IDENTIFIER(cnt)","T_ASSIGNOP","T_NUMLIT(0)","T_SEMICOLON","T_INT",
        "T_IDENTIFIER(random_number)","T_SEMICOLON","T_KEYWORD(input)","T_PARENL",
        "T_IDENTIFIER(random_number)","T_PARENR","T_SEMICOLON",
        "T_COMMENT(# If number is less than/equal to 1, #)","T_COMMENT(# it is not prime #)","T_KEYWORD(if)","T_PARENL",
        "T_IDENTIFIER(n)","T_RATIONALOP","T_NUMLIT(1)","T_PARENR","T_BRACEL","T_KEYWORD(print)","T_PARENL",
        "T_STRINGLIT(\" is NOT prime\")","T_PARENR","T_SEMICOLON","T_BRACER","T_BRACER"]



        

def get_tokenzizer(Tokens=Tokens):
    tokenizer=Tokenizer.Tokens(Tokens)
    return tokenizer.get_tokenizer()

#get tokens like (token type , token value)
tokens=get_tokenzizer(Tokens)

global current_pos
current_pos=0


#if token type is according to grammer then advance
def consume(token=None,expected_type=None):
    global current_pos

    token_type,token_value=token
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    if token_type==expected_type:
        current_pos+=1
    else:
        raise SyntaxError(f"unexpected token type {token_type} , expected {expected_type}")
    
#parse datatype
def parse_datatype(token=None,tokens=tokens):
    global current_pos
    start_pos=current_pos
    if token is None:
        raise SyntaxError("Unexpected EOF")
    try:
        node=check_class_type(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_string(token)
        return node
    except SyntaxError:
        current_pos=start_pos
        
    token_type,_=token
    valid_types = {
        "T_VOID": "void",
        "T_CHAR": "char",
        "T_SHORT": "short",
        "T_INT": "int",
        "T_LONG": "long",
        "T_FLOAT": "float",
        "T_DOUBLE": "double",
        "T_BOOL": "bool",
        "T_AUTO": "auto"
    }
    if token_type in valid_types:
        token_value=valid_types.get(token_type)
        return token_value
    else:
        raise SyntaxError("Unknown datatype")


def parse_digit(token=None):
    digits=['0','1','1','3','4','5','6','7','8','9']
    if token is None:
        raise SyntaxError("Unexpected EOF")
    if token in digits:
        return True
    return False

#check identifier according to grammer rules
def parse_identifier(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,token_value=token
    check_token=False
    check_token=parse_letters(token_value[0])
    if token_value[0]=='_':
        check_token=True
    for char in token_value:
        check_token=parse_digit(char)
        check_token=parse_letters(char)
        if char=='_':
            check_token=True
    
    if check_token == False or token_value==None:
        raise SyntaxError("expected a identifier")
    else:
        return token_value
   
#used for checking string literal
def parse_characters(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    check_token=None
    check_token=parse_digits(token)
    check_token=parse_letters(token)
    
    if check_token is not None:
        return check_token
    else:
        raise SyntaxError(f"unexpected token type {token}")
def parse_escaped_charssq(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    sp_ch=['\n','\r','\t']
    if token in sp_ch:
        return token
    else:
        return None

def parse_string(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,token_value=token
    if token_value[0]=='"' and token_value[-1]=='"':
        return token_value
    else:
        if token_value[0]!='"':
            raise SyntaxError("missing opening quote")
        elif token_value[-1]!='"':
            raise SyntaxError("missing closing quote")

#parsing the digits
def parse_digits(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,token_value=token
    digits=['0','1','2','3','4','5','6','7','8','9']
    
    if token_type=="T_NUMLIT":
        for i in range(len(token_value)):
            if token_value[i] not in digits:
                raise SyntaxError("expected an int")
            
        return int(token_value) #return an integer
    
    elif token_type=="T_FLOATLIT":
        index=token_value.find('.')
        
        if index==-1:
            raise SyntaxError("expected a float")

        prefix=token_value[:index]
        postfix=token_value[index+1:]
        for i in range(len(prefix)):
            if prefix[i] not in digits:
                raise SyntaxError("expected a float")
        
        for i in range(len(postfix)):
            if postfix[i] not in digits:
                raise SyntaxError("expected a float")
       
        return float(token_value) #return a float 
    
    elif token_type=="T_BOOLLIT":
        if token_value != "True" or token_value != "False":
            raise SyntaxError("expected a bool lit")
        
        return True if token_value == "True" else False

#parse letters
def parse_letters(token=None):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    if token>='A' and token<='Z' or token>='a' or token <='z':
        return True
    else:
        return False
        
#parsing function syntax
def parse_function(tokens):
    global current_pos
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    consume(tokens[current_pos],expected_type="T_FUNCTION")
    
    return_type=parse_datatype(tokens[current_pos])
    current_pos+=1
    
    function_name=parse_identifier(tokens[current_pos])
  
    current_pos+=1

    consume(tokens[current_pos],"T_PARENL")

    params = []
    if tokens[current_pos][0] != "T_PARENR":  
        # first parameter
        type_tok=parse_datatype(tokens[current_pos])
        current_pos+=1
        if type_tok is not None:
            value_tok=parse_identifier(tokens[current_pos])

        params.append(("Param",type_tok,value_tok))
        current_pos+=1

        # additional parameters
        while current_pos<len(tokens)-1 and tokens[current_pos][0] == "T_COMMA":
            consume(tokens[current_pos],"T_COMMA")
            type_tok=parse_datatype(token=tokens[current_pos])
            current_pos+=1
            if type_tok is not None:
                value_tok=parse_identifier(tokens[current_pos])

            params.append(("Param",type_tok,value_tok))
            current_pos+=1
    
    consume(tokens[current_pos],"T_PARENR")
    consume(tokens[current_pos],"T_BRACEL")

    body=parse_statements(tokens)

    consume(tokens[current_pos],"T_BRACER")

    return {"Function":"def","return type":return_type,"identifier":function_name,"params":params,"body":body}

#checking for proper keyword 
def parse_keyword(token):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,token_value=token

    keywords=["for","while","if","else","else if",
        "switch","case","do","break","continue","class","struct",
        "public","private","protected","this","Array","delete","try",
        "catch","template","goto","return","len","throw","print","input"]
    
    if token_value in keywords:
        return token_value
    else:
        raise SyntaxError(f"expected a {token_value}")
    

#parsing decleration statement (int x=0)
def parse_decleration(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    data_type=parse_datatype(tokens[current_pos])
    
    current_pos+=1
    name=parse_identifier(tokens[current_pos])

    current_pos+=1

    value = None
    if tokens[current_pos][0] == "T_ASSIGNOP":
        consume(tokens[current_pos],"T_ASSIGNOP")
        value = parse_digits(tokens[current_pos])
        if value is None:
            raise SyntaxError("Expected an expression after '='")

        current_pos += 1

    consume(tokens[current_pos],"T_SEMICOLON")


    return {
        "datatype": data_type,
        "identifier": name,
        "value": value
    }
    
#check for operators
def parse_operators(token):
    if token is None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,_=token
    operators=["T_EQUALSOP","T_ARITHOP","T_ASSIGNOP","T_RATIONALOP","T_LOGICOP", "T_BITWISEOP"]
    if token_type not in operators:
        raise SyntaxError("expected an operator")
      
#parsing expression containing operators to identifier
def parse_operator_expression(tokens):
    global current_pos
    
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    tok_iden=parse_identifier(tokens[current_pos])
    current_pos+=1
    parse_operators(tokens[current_pos])
    current_pos+=1
    if tokens[current_pos][0]=="T_NUMLIT" or tokens[current_pos][0]=="T_FLOATLIT":
        tok_value=parse_digits(tokens[current_pos])
    else:
        tok_value=parse_identifier(tokens[current_pos])

    current_pos+=1

    return {
        "type":"OperatorExpression",
        "identifier":tok_iden,
        "value":tok_value
    }

#parsing  expressions like i->s
def parse_postfix_expression(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos = current_pos  # save for backtracking
   
    try:
        left_id = parse_identifier(tokens[current_pos])
        current_pos += 1 
        consume(tokens[current_pos],"T_ARROW")  
        right_id = parse_identifier(tokens[current_pos])
        current_pos += 1
        return {
            "type":"PostfixExpression",
            "operator": "->",
            "left": left_id,
            "right": right_id
        }
    except SyntaxError:
        current_pos = start_pos #rest pointer if failure

    try:
        left_id = parse_identifier(tokens[current_pos])
        current_pos += 1
        consume(tokens[current_pos],"T_DOT")
        right_id = parse_identifier(tokens[current_pos])
        current_pos += 1
        return {
            "type":"PostfixExpression",
            "operator": ".",
            "left": left_id,
            "right": right_id
        }
    except SyntaxError:
        current_pos = start_pos

    try:
        kw = parse_keyword(tokens[current_pos])
        current_pos += 1
        consume(tokens[current_pos],"T_ARROW")
        right_id = parse_identifier(tokens[current_pos])
        current_pos += 1
        return {
            "type":"PostfixExpression",
            "operator": "->",
            "left": kw,
            "right": right_id
        }
    except SyntaxError:
        current_pos = start_pos

    try:
        kw = parse_keyword(tokens[current_pos])
        current_pos += 1
        consume(tokens[current_pos],"T_DOT")
        right_id = parse_identifier(tokens[current_pos])
        current_pos += 1
        return {
            "type":"PostfixExpression",
            "operator": ".",
            "left": kw,
            "right": right_id
        }
    except SyntaxError:
        current_pos = start_pos

    raise SyntaxError(f"UnExpected token {tokens[current_pos]}")

#check print, input statements
def check_scans(tokens,start_pos):
    global current_pos
    
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
   
    try:
        node=parse_operator_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    
    try:
        node=parse_postfix_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_decleration(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos
    
    try:
        node=parse_string(tokens[current_pos])
        return node
    except SyntaxError:
        current_pos=start_pos

    raise SyntaxError(f"UnExpected token {tokens[current_pos]}")

#check print, input statements
def parse_scanning_expression(tokens):
    global current_pos
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    tok_kw=parse_keyword(tokens[current_pos])
    current_pos+=1
    consume(tokens[current_pos],"T_PARENL")

    #for backtracking
    start_pos=current_pos

    #check for all non-terminal , backtrack if error encountered
    args = []
    node = check_scans(tokens, start_pos)
    args.append(node)

    # Handle comma-separated arguments
    while current_pos<len(tokens)-1 and tokens[current_pos][0] == "T_COMMA":
        consume(tokens[current_pos], "T_COMMA")
        start_pos = current_pos
        node = check_scans(tokens, start_pos)
        args.append(node)

    consume(tokens[current_pos], "T_PARENR")
    consume(tokens[current_pos], "T_SEMICOLON")

    return {
        "type": "ScanningExpression",
        "keyword": tok_kw,
        "args": args
    }

#parsing expression like i+=1, i<=size
def parse_expression(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    try:
        node=parse_operator_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_postfix_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_decleration(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    
    raise SyntaxError(f"unexpected token {tokens[current_pos]}")

#statements having if , else
def parse_conditional_statement(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_PARENL")
        args=parse_expression(tokens)
        consume(tokens[current_pos],"T_PARENR")
        consume(tokens[current_pos],"T_BRACEL")
        body=parse_statement(tokens)
        consume(tokens[current_pos],"T_BRACER")

        return {
            "type":"conditional statement",
            "keyword":kw,
            "args":args,
            "body":body,
        }
    except SyntaxError:
        current_pos=start_pos

    
    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_BRACEL")
        body=parse_statement(tokens)
        consume(tokens[current_pos],"T_BRACER")

        return {
            "type":"conditional statement",
            "keyword":kw,
            "body":body,
        }
    except SyntaxError:
        current_pos=start_pos

    raise SyntaxError(f"unexpected token {tokens[current_pos]}")

#iterations
def parse_iteration_statement(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    #simple iterative statement like for , while
    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_PARENL")
        args=parse_expression(tokens)
        consume(tokens[current_pos],"T_PARENR")
        consume(tokens[current_pos],"T_BRACEL")
        body=parse_statement(tokens)
        consume(tokens[current_pos],"T_BRACER")

        return {
            "type":"iteration",
            "keyword":kw,
            "args":args,
            "body":body,
        }
    except SyntaxError:
        current_pos=start_pos

    #parsing do-while , try-catch like statements
    try:
        kw1=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_BRACEL")
        body1=parse_statement(tokens)
        consume(tokens[current_pos],"T_BRACER")

        kw2=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_PARENL")
        args=parse_expression(tokens)
        consume(tokens[current_pos],"T_PARENR")
        consume(tokens[current_pos],"T_SEMICOLON")

        return {
            "type":"iteration",
            "keyword":kw1,
            "body":body1,
            "keyword":kw2,
            "args":args,
        }
    except SyntaxError:
        current_pos=start_pos

    raise SyntaxError(f"unexpected token {tokens[current_pos]}")

#parse function calls
def function_call(tokens):
    global current_pos
    start_pos=current_pos
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    try:
        node=parse_scanning_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos
    
    args=[]
    tok_value=parse_identifier(tokens[current_pos])
    args.append(("identifier",tok_value))
    current_pos+=1

    consume(tokens[current_pos],"T_PARENL")
    if tokens[current_pos][0]!="T_PARENR":
        args=[]
        tok_value=parse_identifier(tokens[current_pos])
        args.append(("identifier",tok_value))
        current_pos+=1
        while current_pos<len(tokens) and tokens[current_pos][0]=="T_COMMA":
            tok_value=parse_identifier(tokens[current_pos])
            args.append(("identifier",tok_value))
            current_pos+=1
    
    consume(tokens[current_pos],"T_PARENR")
    consume(tokens[current_pos],"T_SEMICOLON")

    return {
        "type":"fn call",
        "args":args
    }

#parsing statemetn like return, break, function call
def parse_jump_statement(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    #goto call
    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        tok_value=parse_identifier(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_SEMICOLON")

        return {
            "type":"jump statement",
            "keyword":kw,
            "identifier":tok_value
        }
    except SyntaxError:
        current_pos=start_pos

    #parsing break, continue, return
    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_SEMICOLON")

        return {
            "type":"jump statement",
            "keyword":kw,
        }
    except SyntaxError:
        current_pos=start_pos

    #return more than one expression
    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        while current_pos<len(tokens)-1 and tokens[current_pos][0]=="T_COMMA":
            node=parse_expression(tokens)
        
        consume(tokens[current_pos],"T_SEMICOLON")

        return {
            "type":"jump statement",
            "keyword":kw,
            "args":node
        }
    except SyntaxError:
        current_pos=start_pos

    #return function calls
    try:
        node=function_call(tokens)
        return {
            "type":"jump statement",
            "args":node
        }
    except SyntaxError:
        current_pos=start_pos

    raise SyntaxError(f"unexpected token {tokens[current_pos]}")

#check for private, public
def check_class(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    kw=parse_keyword(tokens[current_pos])
    current_pos+=1
    consume(tokens[current_pos],"T_COLON")
    body=parse_expression(tokens)
    return {
        "keyword":kw,
        "body":body,
    }

#parsing statements
def parse_statement(tokens):
    global current_pos

    if current_pos>len(tokens) or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    try:
        node=parse_conditional_statement(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_iteration_statement(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_jump_statement(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_expression(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=check_class(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos

    try:
        node=parse_comment(tokens)
        return node
    except SyntaxError:
        current_pos=start_pos
    
    raise SyntaxError(f"UnExpected token {tokens[current_pos]}")

#multiple statements
def parse_statements(tokens):
    global current_pos
    statements = []

    while current_pos < len(tokens)-1:
        try:
            stmt = parse_statement(tokens)  # <statement>
            statements.append(stmt)
        except SyntaxError:
            break

    return {"type": "Statements", "block": statements}

#check for struct or class
def class_statement(tokens):
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    kw=parse_keyword(tokens[current_pos])
    current_pos+=1
    iden=parse_identifier(tokens[current_pos])
    current_pos+=1
    consume(tokens[current_pos],"T_BRACEL")
    body=parse_statements(tokens=tokens)
    consume(tokens[current_pos],"T_BRACER")

    return {
        "keyword":kw,
        "identifier":iden,
        "body":body
    }

#check for class objects  
def check_class_type(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    start_pos=current_pos

    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        iden=parse_identifier(tokens[current_pos])
        current_pos+=1
        iden=parse_identifier(tokens[current_pos])
        current_pos+=1
        
        consume(tokens[current_pos],"T_PARENL")
        args=[]
        tok_value=parse_identifier(tokens[current_pos])
        args.append(tok_value)
        while current_pos<len(tokens)-1 and tokens[current_pos][0]=="T_COMMA":
            tok_value=parse_identifier(tokens[current_pos])
            args.append(tok_value)
        
        return {
            "keyword":kw,
            "identifier":iden,
            "args":args
        }
    except SyntaxError:
        current_pos=start_pos


    try:
        kw=parse_keyword(tokens[current_pos])
        current_pos+=1
        iden=parse_identifier(tokens[current_pos])
        current_pos+=1
        iden=parse_identifier(tokens[current_pos])
        current_pos+=1
        consume(tokens[current_pos],"T_SEMICOLON")
        
        return {
            "keyword":kw,
            "identifier":iden
        }
    except SyntaxError:
        current_pos=start_pos

    raise SyntaxError("unexpected class type")

#check array datatype
def parse_array(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    kw = parse_keyword(tokens[current_pos])
    current_pos += 1

    consume(tokens[current_pos], "T_PARENL")

    node = None
    if tokens[current_pos][0] == "T_NUMLIT":  # digits
        node = parse_digits(tokens[current_pos])
        current_pos += 1
    elif tokens[current_pos][0] == "T_IDENTIFIER":  # identifier
        node = parse_identifier(tokens[current_pos])
        current_pos += 1
    else:
        raise SyntaxError(f"Expected digits or identifier at {tokens[current_pos]}")

    consume(tokens[current_pos], "T_PARENR")

    return {
        "type": "Array",
        "keyword": kw,
        "args": node
    }

#check for pointer for array
def parse_pointer(tokens):
    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    
    dtype = parse_datatype(tokens[current_pos])
    current_pos += 1
    parse_operators(tokens[current_pos])
    current_pos+=1

    ident = parse_identifier(tokens[current_pos])
    current_pos += 1

    if tokens[current_pos][0] == "T_SEMICOLON":
        consume(tokens[current_pos], "T_SEMICOLON")
        
        return {
            "type": "PointerDecl",
            "datatype": dtype,
            "identifier": ident
        }

    elif tokens[current_pos][0] == "T_ASSIGNOP":
        consume(tokens[current_pos], "T_ASSIGNOP")
        arr_node = parse_array(tokens)  
        consume(tokens[current_pos], "T_SEMICOLON")
        return {
            "type": "PointerDecl",
            "datatype": dtype,
            "identifier": ident,
            "init": arr_node
        }

    else:
        raise SyntaxError(f"Expected ';' or '=' after pointer declaration at {tokens[current_pos]}")

#check for bool type
def parse_bool(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos] is None:
        raise SyntaxError("Unexpected EOF")
    dtype = parse_datatype(tokens[current_pos])
    
    current_pos += 1

    ident = parse_identifier(tokens[current_pos])
    current_pos += 1

    if tokens[current_pos][0] == "T_SEMICOLON":
        consume(tokens[current_pos], "T_SEMICOLON")
        return {
            "type": "BoolDecl",
            "datatype": dtype,
            "identifier": ident,
        }

    elif tokens[current_pos][0] == "T_ASSIGNOP":
        consume(tokens[current_pos], "T_ASSIGNOP")

        value=parse_keyword(tokens[current_pos])
        
        current_pos += 1

        consume(tokens[current_pos], "T_SEMICOLON")

        return {
            "type": "BoolDecl",
            "datatype": dtype,
            "identifier": ident,
            "value": True if value == 'True' else False
        }

    else:
        raise SyntaxError(f"Expected ';' or '=' in bool declaration at {tokens[current_pos]}")

#parsing the comment
def parse_comment(tokens):
    global current_pos

    if current_pos>len(tokens)-1 or tokens[current_pos]==None:
        raise SyntaxError("Unexpected EOF")
    
    token_type,token_value=tokens[current_pos]
    current_pos+=1
    if token_value[0]!='#' or token_value[-1]!='#':
        raise SyntaxError("Expected a '#'")
    else:
        return {
            "type":"comment",
            "comment":token_value
        }

#parsing the whole program
def parse_program(tokens):
    program=[]
    while current_pos<len(tokens)-1:
        body=parse_function(tokens)
        program.append(body)

    print(program)


parse_program(tokens)
