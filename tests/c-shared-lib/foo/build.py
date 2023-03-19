def build(gen, env):
    env.shared_lib(gen, out = 'libfoo', ins = ['foo.c'])
