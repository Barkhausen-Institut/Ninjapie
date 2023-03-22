from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CRGFLAGS'] += ['--release']
env['CXXFLAGS'] += ['-Wall', '-Wextra']

env.rust_lib(gen, out='foo')
env.cxx_exe(gen, out='hello', ins=['hello.cpp'], libs=['foo'])

gen.write_to_file(env)
