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

    string::const_iterator start = code.begin();
    string::const_iterator end = code.end();

    while (start != end) {
        bool matched = false;

        for (auto &[type, pattern] : tokenSpecs) {
            smatch match;
            if (regex_search(start, end, match, pattern, regex_constants::match_continuous)) {
                if (type != "WHITESPACE") { // Skip whitespace
                    tokens.push_back({type, match.str()});
                }
                start += match.length(); // move forward
                matched = true;
                break;
            }
        }

        if (!matched) {
            cerr << "Unexpected character: " << *start << endl;
            ++start;
        }
    }

    return tokens;
}

int main() {
    string code = "int x = 10 + 20;\nif(x > 15) return x;";
    vector<Token> tokens = lexer(code);

    for (auto &t : tokens) {
        cout << "[" << t.type << ": " << t.value << "]\n";
    }

    system("pause");
    return 0;

}