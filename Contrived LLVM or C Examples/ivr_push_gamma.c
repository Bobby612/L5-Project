
int main(){
    int a, b, c, d;
    a = 3;
    b = 7;
    c = 22;
    d = 42;

    if (a+c < b+d) {
        c = a + c;
        b++;
    } else {
        c = a + c;
        b--;
    }

    return b + c;

}