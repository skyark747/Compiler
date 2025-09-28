<program>::=<functions>{<functions>};

<functions>::=<data-type><identifier>"(" [<data-type><identifier>]{","{<data-type><identifier>}} ")""{"<statements>"}";

<data-type>::= "void"
            | "char"
            | "short"
            | "int"
            | "long"
            | "float"
            | "double"
            | <bool> 
            | "auto"
            | <string>
            | <struct-or-class-type>;

<pointer>::=<data-type>"*"<identifier>";"| <data-type>"*"<identifier><assignment-operator><Array>";"
<Array>::=<keyword>"("<digits>|<identifier>")"

<bool>::=<data-type><identifier>";"|<data-type><identifier>"="("True"|"False")";"
<string>::="""<characters>""";
<characters>::=<letter>|<digits>|<escaped-chars>;
<escaped-chars>::="\"<escaped-chars-sq>;
<escaped-chars-sq>::="\"|"n"|"t"|"r"|"'";

<struct-or-class-type>::=<keyword> <identifier";"| <keyword> <identifier"("{<identifier>}")"";"
<struct-or-class>::= <keyword> <identifier> "{"<statements>"}"|;

<statements>::={<statement>};

<statement>::=<conditional-statement>";"
            | <iteration-statement>";"
            | <jump-statement>";"
            | <expression>
            | <class-statement>
            | <comment>;

<class-statement>::=<keyword>":"{<expression>}
            
<conditional-statement>::=<keyword>"("<expression>")""{"<statements>"}"
                        | <keyword>"{"<statements>"}";

<iteration-statement>::=<keyword>"("<expression>")""{"<statements>"}"
                    |  <keyword>"{"<statements>"}"<keyword>"("<expression>")"";";

<jump-statement>::= <keyword><identifier>";"
                | <keyword>";"
                | <function-call>";"
                | <keyword>{<expression>}";"; *for return statement*

<function-call>::=<identifier>"(" [<identifier>]{","<identifier>} ")"";"|<scanning-expression>;

<expression>::=<operator-expression>
            | <postfix-expression>
            | <decleration>
            | <scanning-expression>;
            
        
<decleration>::=<data-type><identifier>["="<digits>];

<operator-expression>::= <identifier>operator><digits>
                        | <identifier><operator><identifier>;
                        
<assignment-operator>::= "="
                    
<postfix-expression>::= <identifier> "->"<identifier>
                    | <identifier> "." <identifier>
                    | <keyword> "->" <identifier>
                    | <keyword> "." <identifier>;
                    
<operator>::= "+"|"-"|"*"|"/"|"%"|"|"|"&"|"<"|">"|"!"|"~"|"^"|"+="|"-="|"*="|"/="|"%="|"|="|"&="|"<="|">="|"!="|"~="|"^="
           | "==" | "||" | "&&" | "<<" | ">>","<<=" | ">>=";

<scanning-expression>::=<keyword>"("<expression>|<string>{","<expression>|<string>}")"";";

<keyword>::="for"|"while"|"if"|"else"|"else if"|
        "switch"|"case"|"do"|"break"|"continue"|"class"|"struct"|
        "public"|"private"|"protected"|"this"|"Array"|"delete"|"try"|
        "catch"|"template"|"goto"|"return"|"len"|"throw"|"print"|"input"|"True"|"False";

<identifier>::=(<letter>|"_"){<letter>|<digits>|"_"};

<letter>::= "A" | "B" | "C" | "D" | "E" | "F" | "G"
       | "H" | "I" | "J" | "K" | "L" | "M" | "N"
       | "O" | "P" | "Q" | "R" | "S" | "T" | "U"
       | "V" | "W" | "X" | "Y" | "Z" | "a" | "b"
       | "c" | "d" | "e" | "f" | "g" | "h" | "i"
       | "j" | "k" | "l" | "m" | "n" | "o" | "p"
       | "q" | "r" | "s" | "t" | "u" | "v" | "w"
       | "x" | "y" | "z" ;

<digit>::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;

<digits>::={<digit>};

<float-double>::=<digits>"."<digits>;

<comment>::="#"<characters>"#"

