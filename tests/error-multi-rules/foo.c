#define MK_FUNC_NAME(name, suffix) int name ## suffix(int a, int b)
#define FUNC_NAME(name, suffix)    MK_FUNC_NAME(name, suffix)

FUNC_NAME(foo, TEST) {
    return a + b + TEST;
}
