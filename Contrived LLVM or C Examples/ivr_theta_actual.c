
int main(){
    int a, b, c;
    a = 5;
    b = 10;
    c = 20;
    
    do {
        a = b * b;
        c--;
    } while (c>b);

    return a;
}