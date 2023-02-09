#include <stdlib.h>
#include <stdio.h>

int example(int a, int b, int c, int d);

int global_var1 = 0;
int global_var2;
char * global_var3 = "cool";


int main()
{
    global_var1++;
    global_var2 = global_var1 + 1;
    char cool_1 = global_var3[1];
    int * heapvar = malloc(sizeof(int));
    *heapvar = example(1, 2, global_var1, global_var2);
    puts("so cool");
    return *heapvar;
}

int example(int a, int b, int c, int d)
{
    int acopy, bcopy, lp_inv1, lp_inv2;
    int down, cse, epr, dead;
    while (a > cse)
    {
        bcopy = b;
        lp_inv1 = c + bcopy;
        lp_inv2 = d - b;
        a = a * lp_inv1;
        down = a % c;
        dead = a + d;
        if (a > d)
        {
            acopy = a;
            a = down + 3;
            cse = acopy << b;
        }
        else
            cse = a << bcopy;
        epr = a << b;
    }
    return lp_inv2 + epr;
}
