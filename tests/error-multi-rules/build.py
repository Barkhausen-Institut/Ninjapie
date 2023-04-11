from ninjapie import Generator, Env

gen = Generator()
env = Env()

env1 = env.clone()
env1['CPPFLAGS'] += ['-DTEST=1']
obj1 = env1.cc(gen, out='hello.o', ins=['hello.c'])

env2 = env.clone()
env2['CPPFLAGS'] += ['-DTEST=2']
obj2 = env2.cc(gen, out='hello.o', ins=['hello.c'])

env.c_exe(gen, out='hello', ins=[obj1, obj2])

gen.write_to_file()
