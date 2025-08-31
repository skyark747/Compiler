#include <iostream>
#include <regex>
#include <vector>
#include <string>
using namespace std;

struct Token {
    string type;
    string value;
};

vector<Token> lexer(const string &code) {
    vector<Token> tokens;

    // Token patterns
    vector<pair<string, regex>> tokenSpecs = {
        {"KEYWORD", regex("\\b(int|if|else|while|return)\\b")},
        {"NUMBER", regex("[0-9]+")},
        {"IDENTIFIER", regex("[a-zA-Z_][a-zA-Z0-9_]*")},
        {"OPERATOR", regex("[+\\-*/=<>!]=?|==")},
        {"SYMBOL", regex("[;{},()]")},
        {"WHITESPACE", regex("[ \\t\\n]+")}
    };

    int n = code.size();
    int i = 0;

    while (i < n) {
        bool matched = false;

        for (size_t j = 0; j < tokenSpecs.size(); ++j) {
            
            string type = tokenSpecs[j].first;
            regex pattern = tokenSpecs[j].second;

            for (int len = 1; i + len <= n; ++len) {
            string sub = code.substr(i, len);

            if (regex_match(sub, pattern)) {
                
                if (i + len == n || !regex_match(code.substr(i, len + 1), pattern)) {
                    
                    if (type != "WHITESPACE") {
                        Token t;
                        t.type = type;
                        t.value = sub;
                        tokens.push_back(t);
                    }
                    i += len;       
                    matched = true; 
                    break;          
                    }
                }
            }

            if (matched) {
                break; 
            }
        }


        if (!matched) {
            cerr << "Unexpected character: " << code[i] << endl;
            i++;
        }
    }

    return tokens;
}

int main() {

    // Test
    string code = "int x = 10 + 20;\nif(x > 15) return x;";

    vector<Token> tokens = lexer(code);

    for (int i = 0; i < tokens.size(); i++) {
        cout << "[" << tokens[i].type << ": " << tokens[i].value << "]\n";
    }

    return 0;
}
