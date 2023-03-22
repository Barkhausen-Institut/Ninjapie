from ninjapie import Generator, Env, Rule, BuildEdge, BuildPath, SourcePath


class LatexEnv(Env):
    def tex(self, gen, input, deps=[]):
        pdf = BuildPath.with_file_ext(self, input, 'pdf')
        gen.add_build(BuildEdge(
            'tex',
            outs=[pdf],
            ins=[SourcePath.new(self, input)],
            deps=deps,
            vars={
                'tex': self['TEX'],
                'dir': self['BUILDDIR'],
                'texflags': ' '.join(self['TEXFLAGS'])
            }
        ))
        return pdf


gen = Generator()
env = LatexEnv()

gen.add_rule('tex', Rule(
    cmd='$tex -output-directory=$dir $texflags $in',
    desc='TEX $out'
))

env['TEX'] = 'pdflatex'
env['TEXFLAGS'] = ['-interaction=nonstopmode']
env.tex(gen, 'hello.tex', deps=['example.pdf'])

gen.write_to_file(env)
