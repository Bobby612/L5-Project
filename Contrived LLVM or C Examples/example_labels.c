#include <stdio.h>

int b = 42;
char * c = "Example String";
int a;

int main(int argc, char ** argv){
    
    char d;
    if (b >40){
        a = b/6;
        printf("%d", a);
    } else {
        a = (int) c[0];
        puts(c);
    }
    a = a%argc;
    d = c[a];
    return d;
}