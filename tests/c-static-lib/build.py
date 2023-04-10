from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CFLAGS'] += ['-Wall', '-Wextra', '-pedantic']
env['LIBPATH'] += [env.build_dir]

libs = env.sub_build(gen, 'foo')
assert libs == ['foo']
env.c_exe(gen, out='hello', ins=['hello.c'], libs=libs)

gen.write_to_file()
