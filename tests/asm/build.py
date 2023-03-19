from ninjapie import Generator, Env

gen = Generator()
env = Env()

asm_env = env.clone()
asm_env['CPPFLAGS'] += ['-DRETURN_0']
asm = asm_env.cpp(gen, out = 'hello-cpp.S', ins = ['hello.S'])

bin = env.c_exe(gen, out = 'hello', ins = [asm])
env.strip(gen, out = 'hello-stripped', input = bin)

gen.write_to_file(env)
