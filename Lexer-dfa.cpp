//     #include <iostream>
//     #include<string>
//     #include<vector>

//     using namespace std;


//     struct Token
//     {
//         string token_type;
//         string token_value;
//         /* data */
//     };

//     vector<vector<int>> TransitionTable = {
//     // alp  num  opr  sym  unknow
//         {  1,   2,   3,   4,     -1},//start
//         {  1,   1,   -1,   -1,   -1}, // 0: Identifier
//         {  -2,   2,   -1,   -1,  -1}, // 1: number
//         {  -1,   -1,   2,   -1,  -1}, // 2: operator
//         {  -1,   -1,   -1,   -1,  -1} // 3: symbol
        
//     };
//    vector<string> FinalStates = {
//         "NONE", "IDENTIFIER", "NUMBER", "OPERATOR", "SYMBOL"
//     };

//     int classtype(char ch)
//     {
//         if((ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')||ch=='_')
//             return 0;           //alphabet
//         else if(ch>='0'&&ch<='9')
//             return 1;           //number
//         else if(ch=='+'||ch=='-'||ch=='*'||ch=='/'||ch=='='||ch=='<'||ch=='>'||ch=='!')
//             return 2;           //operator
//         else if(ch==';'||ch==','||ch=='{'||ch=='}'||ch=='('||ch==')')
//             return 3;           //symbol
//         // else if(ch==' '||ch=='\t'||ch=='\n')
//         //     return 4;           //whitespace
//         else
//             return 4;          //unknown
//     }

//     bool isKeyword(const string &word)
//     {
//         static vector<string> keywords = {"for","while","if","else","elseif",
//         "switch","case","do","break","continue","class","struct",
//         "public","private","protected","this","new","delete","try",
//         "catch","template","goto","return","auto","sizeof","throw","cout","cin"};
//         for (auto &kw : keywords) {
//             if (word == kw) return true;
//         }
//         return false;
//     }

//     vector<Token> Lexer(string code)
//     {
//         int start,state = 0;
//         int end=code.size();
//         Token current_token;
//         vector<Token> Tokens;
//         while(start<end)
//         {
//            for(int i=0;i<=end;i++)
//             start=i;
//         }

//     }


//     int main()
//     {

//         string code = "int a = 45; if(a>5) return a;";
//         cout<<code;
//         system("pause");
//         return 0;
//     }

/*
asdbdfasdf
//adbfbsdsfdd
adfadf
/*asdfn
*/
// Columns: 0=alpha, 1=num, 2=operator, 3=symbol, 4=unknown, 5=whitespace, 6=/n
// vector<vector<int>> TransitionTable = {
//     {1,   2,  3,  4, -2, -1},   // 0: Start
//     {1,   1, -1, -1, -2, -1}, // 1: Identifier
//     {-2,  2, -1, -1, -2, -1},// 2: Number
//     {-1, -1,  3, -1, -2, -1},// 3: Operator
//     {-1, -1, -1, -1, -2, -1},// 4: Symbol
// };


    #include <iostream>
#include <string>
#include <vector>
#include <cctype>
using namespace std;

struct Token {
    string token_type;
    string token_value;
};

// DFA Transition Table/*adfab

vector<vector<int>> TransitionTable = {
     // alp0  num1  opr2  sym3  space4 unknown5  s-cmnt6 d-cmnt7 d-cmnt-end8 \n9  quote10
        { 1,    2,    3,    5,   -1,   -2,    6,   7,  -2,  -1,   8 },      //start
        { 1,    1,   -1,   -1,   -1,   -2,   -1,  -1,  -2,  -1,  -1 },      // 1: Identifier
        {-2,    2,   -1,   -1,   -1,   -2,   -1,  -1,  -2,  -1,  -1 },      // 2: number
        {-1,   -1,    4,   -1,   -1,   -2,   -1,  -1,  -2,  -1,  -1 },      // 3: operator`
        {-1,   -1,   -1,   -1,   -1,   -2,   -1,  -1,  -2,  -1,  -1 },      // 4: 2nd operator
        {-1,   -1,   -1,   -1,   -1,   -2,   -1,  -1,  -2,  -1,  -1 },      // 5: symbol
        { 6,    6,    6,    6,    6,    6,    6,   6,  -2,  -1,   6 },      // 6: s-cmnt
        { 7,    7,    7,    7,    7,    7,    7,   7,  -1,   7,   7 },      // 7: d-cmnt
        { 8,    8,    8,    8,    8,    8,    8,   8,   8,   8,  -1 }       // 8:qutation mark

        
    };

vector<string> FinalStates = {
    "NONE", "IDENTIFIER", "NUMBER", "OPERATOR", "Double-operator","SYMBOL","single-comment","multi-comment","quotation-mark"
};

// Classify character
int classtype(char ch,char next_ch,char prev_ch) {

    if (isalpha(ch) || ch == '_') 
        return 0;                                                 // alpha

    else if (isdigit(ch)) 
        return 1;                                                 // digit

    else if (ch==';'||ch==','||ch=='{'||ch=='}'||ch=='('||ch==')'||ch=='['||ch==']')
        return 3;                                                  // symbol

    else if(ch=='/'&& next_ch=='/'|| (ch=='/'&& prev_ch=='/'))
         return 6;                                                 // single-line comment
    
    else if(ch=='/'&& next_ch=='*'||(ch=='*'&& prev_ch=='/'))
            return 7;                                               // multi-line comment
    
    else if((ch=='/'&& prev_ch=='*'))
            return 8;                                                // multi-line comment end
    
    else if (ch=='+'||ch=='-'||ch=='*'||ch=='/'||ch=='='||ch=='<'||ch=='>'||ch=='!'||ch=='%'||ch=='&'||ch=='|')
              return 2;                                              // operator
    else if (ch=='\n')
        return 9;
    else if(ch=='"')
        return 10;

    else if (isspace(ch))
        return 4;                                                    // whitespace
    
    else return 5;                                                   // unknown
}

// Check if keyword
bool isKeyword(const string &word) {
    static vector<string> keywords = {"for","while","if","else","elseif",
"switch","case","do","break","continue","class","struct",
"public","private","protected","this","new","delete","try",
"catch","template","goto","return","auto","sizeof","throw","cout","cin",
"int","short","long","float","double","char","bool","void","wchar_t",
"signed","unsigned","enum","union","typedef","using","main",
"char16_t","char32_t","nullptr_t","decltype"
};
    for (auto &kw : keywords) {
        if (word == kw) return true;
    }
    return false;
}

vector<Token> Lexer(string code) {
    vector<Token> tokens;
    int state = 0;
    string current;

    for (size_t i = 0; i <= code.size(); i++) {
        char ch = (i < code.size() ? code[i] : ' '); // add space at end
        int type = classtype(ch, (i + 1 < code.size() ? code[i + 1] : ' '), (i > 0 ? code[i - 1] : ' '));

        int next = TransitionTable[state][type];

        if (next == -1 || next == -2) {
            if (!current.empty() && state > 0) {
                if(state==8||state==7)
                    current+=ch;
                
                string tokenType = FinalStates[state];
                if (tokenType == "IDENTIFIER" && isKeyword(current))
                   tokenType = "KEYWORD";

                tokens.push_back({tokenType, current});
                current.clear();
            }
            state = 0;
            if (type == 5) {
                cerr << "Error: Unknown character '" << ch << "'\n";
            }
        } else if (type != 5) { // ignore whitespace

                current += ch;
                state = next;
        } else {
            if (!current.empty() && state > 0) {
                if(state==10||state==9)
                    current+=ch;
                
                string tokenType = FinalStates[state];
                if (tokenType == "IDENTIFIER" && isKeyword(current))
                    tokenType = "KEYWORD";
                tokens.push_back({tokenType, current});
                current.clear();
            }
            state = 0;
        }
    }
    return tokens;
}

int main() {
    string code = R"(int main () {
        int n = 29;
        int cnt = 0;
        
        // If number is less than/equal to 1,
        // it is not prime
        if (n <= 1)
            cout << n << " is NOT prime";
        else {

            // Count the divisors of n
            for (int i = 1; i <= n; i++) {
                if (n % i == 0)
                    cnt++;
            }

            // If n is divisible by more than 2 
            // numbers then it is not prime
            if (cnt > 2)
                cout << n << " is NOT prime";

            // else it is prime
            else
                cout << n << " is prime";
            
        }
        return 0;
    })";
 

    vector<Token> tokens = Lexer(code);

    for (auto &t : tokens) {
        cout << "[" << t.token_type << ": " << t.token_value << "]"<<", ";
    }
    system("pause");
    return 0;
}
