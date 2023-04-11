#include <stdio.h>

extern int foo1(int a, int b);
extern int foo2(int a, int b);

int main() {
    printf("Hello %d!\n", foo1(12, 14) + foo2(10, 3));
    return 0;
}
