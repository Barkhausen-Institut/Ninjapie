from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CFLAGS'] += ['-Wall', '-Wextra']
env.shared_lib(gen, out='foo', ins=['foo.c'])

gen.write_to_file(env)
