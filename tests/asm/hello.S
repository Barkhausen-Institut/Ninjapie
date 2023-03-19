.global main
main:
#if defined(RETURN_0)
    mov $0, %rax
#else
    mov $1, %rax
#endif
    ret
