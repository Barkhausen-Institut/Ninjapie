def build(gen, env):
    env.static_lib(gen, out = 'foo', ins = env.glob('*.c'))
