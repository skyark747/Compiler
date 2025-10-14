#include <iostream>
#include <string>
#include <unordered_map>
#include <string.h>
#include <vector>
#include <cctype>
#include <fstream>
using namespace std;

// code for returning true if the word read is a keyword
bool isKeyword(string input)
{
    string keywords []={"for","while","if","else","elseif",
        "switch","case","do","break","continue","class","struct",
        "public","private","protected","this","Array","delete","try",
        "catch","template","goto","return","len","throw","print","input","True","False"
    };

    for(int i=0;i<(sizeof(keywords)/sizeof(keywords[0]));i++) {
        if(input==keywords[i]) {
            return true;
        }
    }
    return false;
}

//return the name of Token as per class of operators
string operatorName(string input) {
    
    const string ar_op[] = {"+", "-", "*", "/", "%","+=","-=","*=","/=" };
    const string as_op[] = {"="};
    const string rl_op[] = {"!", ">", "<","<=",">=","!=" };
    const string lg_op[] = { "&&", "||" };
    const string bt_op[] = { "&", "|", "^", "~", "<<", ">>","&=","|=","^=","~=","<<=",">>=" };

    if(input=="==")
        return "T_EQUALSOP("+input+")";

    for (int i=0;i<(sizeof(ar_op)/sizeof(ar_op[0]));i++) {
        if(input==ar_op[i]) {
            return "T_ARITHOP("+input+")";
        }
    }

    for (int i=0;i<(sizeof(as_op)/sizeof(as_op[0]));i++) {
        if(input==as_op[i]) {
            return "T_ASSIGNOP("+input+")";
        }
    }

    for (int i=0;i<(sizeof(rl_op)/sizeof(rl_op[0]));i++) {
        if(input==rl_op[i]) {
            return "T_RATIONALOP("+input+")";
        }
    }

    for (int i=0;i<(sizeof(lg_op)/sizeof(lg_op[0]));i++) {
        if(input==lg_op[i]) {
            return "T_LOGICOP("+input+")";
        }
    }

    for (int i=0;i<(sizeof(bt_op)/sizeof(bt_op[0]));i++) {
        if(input==bt_op[i]) {
            return "T_BITWISEOP("+input+")";
        }
    }
    return "NONE";
}
bool isOperator(string input) {
    if(operatorName(input)!="NONE")
        return true;
    return false;
}

//return the token for data type
string dataType(string input) {
    unordered_map<string, string> M = {
        {"int", "T_INT"},
        {"float", "T_FLOAT"},
        {"double", "T_DOUBLE"},
        {"long", "T_LONG"},
        {"short", "T_SHORT"},
        {"bool", "T_BOOL"},
        {"char", "T_CHAR"},
        {"void", "T_VOID"},
        {"string","T_STRING"}
    };

    auto it=M.find(input);
    if(it!=M.end()) {
        return it->second;
    }
    return "NONE"; 
}
bool isdataType(string input) {
    if(dataType(input)!="NONE")
        return true;
    return false;
}

//return left bracket token
string brackettypeLeft(const char* input) {
   char* bracket_type = "NONE";

    if (strcmp(input, "(") == 0)
        bracket_type = "T_PARENL";
    else if (strcmp(input, "[") == 0)
        bracket_type = "T_BRACKL";
    else if (strcmp(input, "{") == 0)
        bracket_type = "T_BRACEL";

    return bracket_type;
}
bool isbrackettypeL(string input) {
    if(brackettypeLeft(input.c_str())!="NONE")
        return true;
    return false;
}

//return right bracket token
string brackettypeRight(const char* input) {
    char* bracket_type = "NONE";

    if (strcmp(input, ")") == 0)
        bracket_type = "T_PARENR";
    else if (strcmp(input, "]") == 0)
        bracket_type = "T_BRACKR";
    else if (strcmp(input, "}") == 0)
        bracket_type = "T_BRACER";

    return bracket_type;
}
bool isbrackettypeR(string input) {
    if(brackettypeRight(input.c_str())!="NONE")
        return true;
    return false;
}

//return token based on some delimiters
string extraDel(string input) {
    if(input==",") 
        return "T_COMMA";
    else if(input==";")
        return "T_SEMICOLON";
    else if(input==":")
        return "T_COLON";
    
    return "NONE";
}
bool isextraDel(string input) {
    if(extraDel(input)!="NONE")
        return true;
    return false;
}

bool isstringLit(char input) {
    if(input=='\n' || input=='\t')
        return true;
    return false;
}

//finding delimeters for breaking the code stream into pieces
bool isDelimiter(char input) {

    const char del[]={' ',',',';','+','-','*','/','%','=','!','&','|','<','>','^','~','(','[','{',')',']','}','\n','\t','\r'};

    for(int i=0;i<sizeof(del)/sizeof(del[0]);i++) {
        if(input==del[i]) {
            return true;
        }
    }
    return false;
}

// check if an input is valid meaning string is not starting from a number
bool isIdentifier(string input) 
{   
    if (input[0]!='0' && input[0]!='1' && input[0]!='2' && input[0]!='3' && input[0]!='4'
    && input[0]!='5' && input[0]!='6' && input[0]!='7' && input[0]!='8' && input[0]!='9' && input[0]!='"' && input!="\n" 
    && input!="\t" && !isdataType(input)) {
        return true;
    }
    return false;
}
//check for non-valid identifier
bool identifierCheck(string input) 
{   
    if((isdigit(input[0]) && isalpha(input[1]))) {
        return true;
    }
    return false;
}

bool isInteger(const char* str)
{
    if (str == NULL || *str == '\0') {
        return false;
    }
    if(isdigit(str[0])) {
        return true;
    }
    return false;
}

void Tokenize(string str,vector<string>&Tokens) {
    int left=0;
    int right=0;

    const string invalid_op_combos[] = {
        // Arithmetic chaining
        "*/", "/*", "/-", "+*", "+/", "-*", "-/", "%/", "%*",

        // Relational mixed
        "<>", "><", "<!", ">!", "=<", "=>",

        // Assignment misuses
        "=+", "=-", "=*", "=/", "=%", "=!", "=<", "=>", "=&", "=|", "=^", "=~",
    };


    while(right<str.length() && left<=right) {
        
        //tokenizing comments
        if (right < str.size() && str[right] == '#')
        {
            int start = right;
            right++;  // move past first '#'

            // find closing '#'
            while (right < str.size() && str[right] != '#')
                right++;

            if (right < str.size())  // found closing '#'
                right++;  // include the closing '#'

            Tokens.push_back("T_COMMENT(" + str.substr(start, right - start) + ")");
            left = right;
            continue;
        }

        //tokenzing string literals
        else if (str[right] == '"') {
            int start = right;
            right++;

            while (right < str.size() && str[right] != '"') {
                if (str[right] == '\\' && right + 1 < str.size())
                    right += 2;
                else
                    right++;
            }

            right++;

            string literal = str.substr(start, right - start);
            if(literal[literal.length()-1]!='"') {
                throw string("Unterminated string literal");
            }
            Tokens.push_back("T_STRINGLIT(" + literal + ")");

            left = right;
            continue;
        }
        while(right<str.length() && !isDelimiter(str[right])) {
            right++;
        }
        
        if(right<str.length() && isDelimiter(str[right]) && left==right) {
            string del;
            del=str[right];
      
            if(isOperator(del)){
                string check_op;
                int check_p=right+1;
                check_op=str[check_p];

                if (isOperator(check_op)){
                    del+=check_op;
                    right++;
                }
                for (int i=0;i<(sizeof(invalid_op_combos)/sizeof(invalid_op_combos[0]));i++) {
                    if(del==invalid_op_combos[i]) {
                        del.pop_back();
                    }
                }
                string op=operatorName(del);
                Tokens.push_back(op);        
            }
            else if(isbrackettypeL(del)) {
                string bracket=brackettypeLeft(del.c_str());
                Tokens.push_back(bracket);
                
            }
            else if(isbrackettypeR(del)) {      
                string bracket=brackettypeRight(del.c_str());
                Tokens.push_back(bracket);
            }
            else if(isextraDel(del)) {
                string ex_del=extraDel(del);
                Tokens.push_back(ex_del);
            }
           
            right++;
        }   
        else if(right<str.length() && isDelimiter(str[right]) && left!=right) {
            int sub_size=right-left;
            string substr=str.substr(left,sub_size);

            if(isKeyword(substr)) {
                
                Tokens.push_back("T_KEYWORD("+substr+")");
            }
            else if(substr=="def") {
                
                Tokens.push_back("T_FUNCTION");
            }
            else if(isIdentifier(substr)){
                  
                Tokens.push_back("T_IDENTIFIER("+substr+")");
            }
            else if(identifierCheck(substr)) {
                if(!isIdentifier(substr)){
                    throw string("wrong identifier");
                }
            }
            else if(isdataType(substr)) {
                string type=dataType(substr);
                Tokens.push_back(type);
                
            }                
            else if(isInteger(substr.c_str())){
                int pos=substr.find('.');
                if(pos!=string::npos)
                    Tokens.push_back("T_FLOATNLIT("+substr+")");
                else
                    Tokens.push_back("T_NUMLIT("+substr+")");
            }
            
        }
        
        left=right;

    }

}

int main(int argc, char* argv[])
{
    vector<string>Tokens;
    
    //string str = "R(def int main(){if(z+=b && f==c) { print(n);}})";

    string str = argv[1];

    try {
        Tokenize(str,Tokens);
    }catch(string &err){
        cout<<err;
    }

    ofstream wr;
    wr.open("lexer_output.txt");
    
    for(int i=0;i<Tokens.size();i++) {
        wr<<Tokens[i]<<"\n";
        
    }

    wr.close();

    cout<<"tokens successfully written in lexer_output.txt";


    return 0;
}