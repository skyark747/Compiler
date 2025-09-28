
class Tokens:
    def __init__(self,tokens):
        self.tokens=tokens
        self.tokenizer=[]
    def break_function(self):
        for token in self.tokens:
            i=token.find('(')
            if i!=-1:
                token_type=token[:i]
                token_value=token[i+1:len(token)-1]
                self.tokenizer.append((token_type,token_value))
            else:
                self.tokenizer.append((token,"None"))

    def get_tokenizer(self):
        self.break_function()
        return self.tokenizer
    
