def build(gen, env):
    env.static_lib(gen, out = 'foo', ins = ['foo.c'])
