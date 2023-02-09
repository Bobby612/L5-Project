

int main(){
    int i,j,k,l,m;
    i = 2 + 2;
    j = i + i;
    l = j + j;
    j = i + j;
    j = i + j;
    if(j == 4){
        l = l + l;
    } else {
        l = j + j;
    }

    return l;
}