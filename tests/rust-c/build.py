from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CRGFLAGS'] += ['--release']
env['CXXFLAGS'] += ['-Wall', '-Wextra']
env['LIBPATH'] += [env.build_dir]

lib = env.rust_lib(gen, out='foo')
env.install(gen, outdir=env.build_dir, input=lib)
env.cxx_exe(gen, out='hello', ins=['hello.cpp'], libs=['foo'])

gen.write_to_file()
