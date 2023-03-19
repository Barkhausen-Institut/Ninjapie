def build(gen, env):
    env.shared_lib(gen, out = 'foo', ins = ['foo.c'])
