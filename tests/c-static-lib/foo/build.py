def build(gen, env):
    env.static_lib(gen, out = 'libfoo', ins = ['foo.c'])
