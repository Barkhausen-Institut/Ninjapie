from ninjapie import Generator, Env

gen = Generator()
env = Env()

env1 = env.clone()
env1['CPPFLAGS'] += ['-DTEST=1']
obj1 = env1.cc(gen, out='foo.o', ins=['foo.c'])

env2 = env.clone()
env2['CPPFLAGS'] += ['-DTEST=2']
obj2 = env2.cc(gen, out='foo.o', ins=['foo.c'])

env.c_exe(gen, out='hello', ins=[obj1, obj2, 'hello.c'])

gen.write_to_file()
