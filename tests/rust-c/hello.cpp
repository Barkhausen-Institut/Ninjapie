#include <iostream>

extern "C" int foo(int a, int b);

int main() {
    std::cout << "Hello " << foo(12, 13) << "!" << std::endl;
    return 0;
}
