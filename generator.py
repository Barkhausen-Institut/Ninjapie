import os
import re
from glob import glob

class Rule:
    def __init__(self, cmd: str, desc: str, deps: str = '', depfile: str = '',
                 generator: str = '', pool: str = '', restat: bool = False):
        assert cmd != '' and desc != ''
        self.cmd = cmd
        self.desc = desc
        self.deps = deps
        self.depfile = depfile
        self.generator = generator
        self.pool = pool
        self.restat = restat
        self.refs = 0

    def _write_to_file(self, name: str, file):
        file.write('rule %s\n' % name)
        file.write('  command = %s\n' % self.cmd)
        file.write('  description = %s\n' % self.desc)
        if self.deps != '':
            file.write('  deps = %s\n' % self.deps)
        if self.depfile != '':
            file.write('  depfile = %s\n' % self.depfile)
        if self.generator != '':
            file.write('  generator = %s\n' % self.generator)
        if self.pool != '':
            file.write('  pool = %s\n' % self.pool)
        if self.restat:
            file.write('  restat = 1\n')

class BuildEdge:
    def __init__(self, rule: str, outs: list[str], ins: list[str], deps: list[str] = [],
                 vars: dict[str, str] = {}, pre_deps: list[str] = [], lib_path: list[str] = []):
        self.rule = rule
        self.outs = outs
        self.ins = ins
        # copy the dependencies, because we want to alter them for this specific BuildEdge later
        self.deps = deps.copy()
        # without inputs and dependencies, we always want to rebuild it
        if self.rule != 'phony' and len(self.ins) == 0 and len(self.deps) == 0:
            self.deps = ['always']
        self.pre_deps = pre_deps
        self.lib_path = lib_path
        self.vars = vars

    def _write_to_file(self, defaults: dict[str, str], file):
        file.write('build %s: %s %s' % (' '.join(self.outs), self.rule, ' '.join(self.ins)))
        if len(self.deps) > 0:
            file.write(' | %s' % (' '.join(self.deps)))
        file.write('\n')
        for k, v in self.vars.items():
            if not k in defaults or defaults[k] != v:
                file.write('  %s = %s\n' % (k, v))

class Generator:
    def __init__(self):
        self.rules = {}
        self.build_edges = []

        # default rules
        self.add_rule('install', Rule(
            cmd = 'install $instflags $in $out && touch $out',
            desc = 'INSTALL $out'
        ))
        self.add_rule('cpp', Rule(
            cmd = '$cpp -MD -MF $out.d -P $cppflags $in -o $out',
            deps = 'gcc',
            depfile = '$out.d',
            desc = 'CPP $out'
        ))
        self.add_rule('cc', Rule(
            cmd = '$cc -MD -MF $out.d $ccflags -c $in -o $out',
            deps = 'gcc',
            depfile = '$out.d',
            desc = 'CC $out'
        ))
        self.add_rule('cxx', Rule(
            cmd = '$cxx -MD -MF $out.d $cxxflags -c $in -o $out',
            deps = 'gcc',
            depfile = '$out.d',
            desc = 'CXX $out'
        ))
        self.add_rule('ar', Rule(
            cmd = '$ar $arflags $out $in && $ranlib $out',
            desc = 'AR $out'
        ))
        self.add_rule('link', Rule(
            cmd = '$link -o $out $in $linkflags',
            desc = 'LINK $out'
        ))
        self.add_rule('shlink', Rule(
            cmd = '$shlink -shared -o $out $in $shlinkflags',
            desc = 'SHLINK $out'
        ))
        self.add_rule('strip', Rule(
            cmd = '$strip -o $out $in',
            desc = 'STRIP $out'
        ))
        self.add_rule('cargo', Rule(
            cmd = 'cd $dir && $env cargo $cargoflags',
            desc = 'CARGO $out',
            # recheck which output files have changed after the command to only relink the
            # executables where the library generated by Rust actually changed
            restat = True,
        ))

        # special build edge for 'always-rebuild' build edges
        self.build_edges.append(BuildEdge(
            'phony',
            outs = ['always'],
            ins = [],
            deps = []
        ))

    def add_rule(self, name: str, rule: str):
        assert name not in self.rules
        self.rules[name] = rule

    def add_build(self, edge: BuildEdge):
        assert edge.rule in self.rules
        self.rules[edge.rule].refs += 1
        self.build_edges.append(edge)

    def write_to_file(self, env):
        outdir = env['BUILDDIR']

        build_file = outdir + '/build.ninja'
        dep_file = outdir + '/.build.deps'

        # rules and build edge to automatically regenerate the build.ninja
        self.add_rule('generator', Rule(
            cmd = 'python -B build.py',
            depfile = outdir + '/.build.deps',
            pool = 'build_pool',
            generator = '1',
            desc = 'Regenerating build.ninja',
        ))
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.add_build(BuildEdge(
            'generator',
            outs = [build_file],
            ins = [],
            deps = glob(this_dir + "/*.py"),
        ))

        self._finalize_deps()
        defaults = self._determine_defaults()

        # generate build.ninja
        with open(build_file, 'w') as file:
            file.write('# This file has been generated by the ninjapie build system.\n')
            file.write('\n')

            for k, v in defaults.items():
                file.write('%s = %s\n' % (k, v))
            file.write('\n')

            for n, r in self.rules.items():
                if r.refs > 0:
                    r._write_to_file(n, file)
            file.write('\n')

            # use a separate pool for the build.ninja regeneration to run that alone
            file.write('pool build_pool\n')
            file.write('  depth = 1\n')
            file.write('\n')

            for b in self.build_edges:
                b._write_to_file(defaults, file)

        # generate deps of build.ninja
        build_files = ['build.py'] + glob('./**/build.py', recursive = True)
        with open(dep_file, 'w') as deps:
            deps.write(build_file + ': ' + ' '.join(build_files))

    def write_compile_cmds(self, env):
        outdir = env['BUILDDIR']

        # generate compile_commands.json for clangd
        with open(outdir + '/compile_commands.json', 'w') as cmds:
            cmds.write('[\n')
            base_dir = os.getcwd()
            c = 0
            for b in self.build_edges:
                if b.rule == 'cxx' or b.rule == 'cc':
                    assert len(b.ins) == 1
                    if c > 0:
                        cmds.write(',\n')
                    cmds.write('  {\n')
                    cmds.write('    "directory": "{}",\n'.format(base_dir))
                    cmds.write('    "file": "{}",\n'.format(b.ins[0]))
                    cmds.write('    "command": "{}"\n'.format(self._get_clang_flags(b)))
                    cmds.write('  }')
                    c += 1
            cmds.write('\n]\n')

    def _get_clang_flags(self, bedge: BuildEdge) -> str:
        flags = 'ccflags' if bedge.rule == 'cc' else 'cxxflags'
        flag_str = bedge.vars[flags].replace('"', '\\"')
        flag_str = 'clang ' + flag_str if bedge.rule == 'cc' else 'clang++ ' + flag_str
        # remove all machine specific flags, because clang does not support all ISAs, etc.
        return re.sub(r'\s+-m\S+', '', flag_str)

    def _determine_defaults(self) -> dict[str, str]:
        # first count the number of times for each value and each variable
        vars = {}
        for b in self.build_edges:
            for k, v in b.vars.items():
                if not k in vars:
                    vars[k] = {}
                if v in vars[k]:
                    vars[k][v] += 1
                else:
                    vars[k][v] = 1

        # now use the most-used value for each variable as the default
        defaults = {}
        for name, vals in vars.items():
            max_count = 0
            max_key = None
            for key, count in vals.items():
                if count > max_count:
                    max_key = key
                    max_count = count
            if not max_key is None:
                defaults[name] = max_key
        return defaults

    def _finalize_deps(self):
        libs = self._collect_libs()
        for b in self.build_edges:
            for d in b.pre_deps:
                stname = 'lib' + d + '.a'
                shname = 'lib' + d + '.so'
                for p in b.lib_path:
                    if p in libs:
                        if shname in libs[p]:
                            b.deps.append(libs[p][shname])
                            break
                        elif stname in libs[p]:
                            b.deps.append(libs[p][stname])
                            break

    def _collect_libs(self) -> dict[str, dict[str, str]]:
        libs = {}
        for b in self.build_edges:
            for o in b.outs:
                if o.endswith('.a') or o.endswith('.so'):
                    dir = os.path.dirname(o)
                    if not dir in libs:
                        libs[dir] = {}
                    libs[dir][os.path.basename(o)] = o
        return libs
