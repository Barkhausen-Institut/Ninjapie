#include <stdio.h>

#include "foo.h"

#ifdef MY_CONSTANT
#   error "This constant should not exist"
#endif

int main() {
    printf("Hello %d!\n", foo(10, 14));
    return 0;
}
