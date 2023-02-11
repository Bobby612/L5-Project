
int main(){
    int a,b,c,d;
    a = 1;
    b = 2;
    c = 3;
    d = 4;

    a = b+c;
    
    if (b > d) {
        b = a;
    } else {
        d = c+c;
    }   
    return d+b;
}