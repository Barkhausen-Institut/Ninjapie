from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CXXFLAGS'] += ['-Wall', '-Wextra']
env.cxx_exe(gen, out='hello', ins=['hello.cc'])

gen.write_to_file(env)
