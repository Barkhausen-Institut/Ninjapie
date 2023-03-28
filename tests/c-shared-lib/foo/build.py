def build(gen, env):
    lib = env.shared_lib(gen, out='foo', ins=['foo.c'])
    env.install(gen, outdir=env.build_dir, input=lib)
