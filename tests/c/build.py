from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CFLAGS'] += ['-Wall', '-Wextra']
env.c_exe(gen, out = 'hello', ins = ['hello.c'])

gen.write_to_file(env)
