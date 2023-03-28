def build(gen, env):
    lib = env.static_lib(gen, out='foo', ins=env.glob(gen, '*.c'))
    env.install(gen, outdir=env.build_dir, input=lib)
