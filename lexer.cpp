#include <iostream>
#include <string>
#include <unordered_map>
#include <string.h>
#include <vector>
#include <cctype>
using namespace std;

// code for returning true if the word read is a keyword
bool isKeyword(string input)
{
    string keywords []={"for","while","if","else","elseif",
        "switch","case","do","break","continue","class","struct",
        "public","private","protected","this","new","delete","try",
        "catch","template","goto","return","auto","sizeof","throw","cout","cin"
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
    
    const string ar_op[] = { "+", "-", "*", "/", "%" };
    const string as_op[] = {"="};
    const string rl_op[] = { "==", "!=", ">", "<", ">=", "<=" };
    const string lg_op[] = { "&&", "||", "!" };
    const string bt_op[] = { "&", "|", "^", "~", "<<", ">>" };

    for (int i=0;i<(sizeof(ar_op)/sizeof(ar_op[0]));i++) {
        if(input==ar_op[i]) {
            return "T_ARITHOP";
        }
    }

    for (int i=0;i<(sizeof(as_op)/sizeof(as_op[0]));i++) {
        if(input==as_op[i]) {
            return "T_ASSIGNOP";
        }
    }

    for (int i=0;i<(sizeof(rl_op)/sizeof(rl_op[0]));i++) {
        if(input==rl_op[i]) {
            return "T_RATIONALOP";
        }
    }

    for (int i=0;i<(sizeof(lg_op)/sizeof(lg_op[0]));i++) {
        if(input==lg_op[i]) {
            return "T_LOGICOP";
        }
    }

    for (int i=0;i<(sizeof(bt_op)/sizeof(bt_op[0]));i++) {
        if(input==bt_op[i]) {
            return "T_BITWISEOP";
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

    const char del[]={' ',',',';','+','-','*','/','%','=','!','&','|','<','>','^','~','(','[','{',')',']','}'};

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

void Tokenize(string str,vector<string>&Tokens) {
    int left=0;
    int right=0;

    while(right<str.length() && left<=right) {
        
        //tokenizing comments
        if (right + 1 < str.size() && str[right] == '/')
        {
                if (str[right + 1] == '/')
                {
                    int start = right;
                    right += 2;
                    while (right + 1 < str.size() && str[right] != '\n') 
                        right++;
                    Tokens.push_back("T_COMMENT(" + str.substr(start, right - start) + ")");

                    left = right;            
                    continue;                
                }

                if (str[right + 1] == '*')
                {
                    int start = right;
                    right += 2;
                    while (right + 1 < str.size() && !(str[right] == '*' && str[right + 1] == '/')) 
                        right++;

                    right += 2;
                    Tokens.push_back("T_COMMENT(" + str.substr(start, right - start) + ")");

                    left = right;
                    continue;
                }
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
        //tokenzing escaped characters
        else if(isstringLit(str[right])) {
                if(str[right]=='\n') {
                    Tokens.push_back("T_STRINGLIT('/n')");
                }
                else if(str[right]=='\t') {
                    Tokens.push_back("T_STRINGLIT('/t')");
                } 
            right++;
            left=right;     
        }    
        while(right<str.length() && !isDelimiter(str[right])) {
            right++;
        }
        
        if(right<str.length() && isDelimiter(str[right]) && left==right) {
            string del;
            del=str[right];
      
            if(isOperator(del)) {
                
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
            left=right;
        }   
        if(right<str.length() && isDelimiter(str[right]) && left!=right) {
            int sub_size=right-left;
            string substr=str.substr(left,sub_size);

            if(isKeyword(substr)) {
                Tokens.push_back("T_KEYWORD("+substr+")");
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
            else{
                int pos=substr.find('.');
                if(pos!=string::npos)
                    Tokens.push_back("T_FLOATNLIT("+substr+")");
                else
                    Tokens.push_back("T_NUMLIT("+substr+")");
            }
            
            left=right;
            
        }

    }

}

int main()
{
    vector<string>Tokens;
    string str = R"(int main() {
        int n = 29;
        int cnt = 0;
        // If number is less than/equal to 1, it is not prime
        if (n <= 1)
            cout << n << " is NOT prime";
        else { 
            // Count the divisors of n
            for (int i = 1; i <= n; i++) {
                if (n % i == 0)
                    cnt++;
            }
         // If n is divisible by more than 2 numbers then it is not prime
            if (cnt > 2)
                cout << n <<  "is NOT prime";
            else 
                cout << n << " is prime";
        }
        return 0;
        })";

        
    try {
        Tokenize(str,Tokens);
    }catch(string &err){
        cout<<err;
    }

    for(int i=0;i<Tokens.size();i++) {
        cout<<Tokens[i]<<" ";
    }

    return 0;
}