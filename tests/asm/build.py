from ninjapie import Generator, Env

gen = Generator()
env = Env()

env.c_exe(gen, out = 'hello', ins = ['hello.S'])

gen.write_to_file(env)
