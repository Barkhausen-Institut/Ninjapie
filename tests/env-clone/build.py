from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CFLAGS'] += ['-Wall', '-Wextra']

foo_env = env.clone()
foo_env.add_flag('CPPFLAGS', '-DMY_CONSTANT=42')
foo_env.remove_flag('CFLAGS', '-Wextra')
obj = foo_env.cc(gen, out = 'foo.o', ins = ['foo.c'])

env.c_exe(gen, out = 'hello', ins = ['hello.c', obj])

gen.write_to_file(env)
