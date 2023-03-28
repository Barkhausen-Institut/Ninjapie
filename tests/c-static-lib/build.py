from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CFLAGS'] += ['-Wall', '-Wextra', '-pedantic']
env['LIBPATH'] += [env.build_dir]

env.sub_build(gen, 'foo')
env.c_exe(gen, out='hello', ins=['hello.c'], libs=['foo'])

gen.write_to_file()
