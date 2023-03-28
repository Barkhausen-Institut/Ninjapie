from ninjapie import Generator, Env

gen = Generator()
env = Env()

env['CRGFLAGS'] += ['--release']
bin = env.rust_exe(gen, out='hello')
env.install(gen, outdir=env.build_dir, input=bin)
env.strip(gen, out='hello-stripped', input=bin)

gen.write_to_file()
