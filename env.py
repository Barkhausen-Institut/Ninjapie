import copy
from glob import glob
import importlib
import os

from path import BuildPath, SourcePath
from generator import BuildEdge, Generator

class Location:
    def __init__(self, path: str):
        self.path = path

class Env:
    def __init__(self):
        self.cwd = Location('.')

        self.vars = {}

        # default tools
        self.vars['CXX']         = 'g++'
        self.vars['CPP']         = 'cpp'
        self.vars['AS']          = 'gcc'
        self.vars['CC']          = 'gcc'
        self.vars['AR']          = 'gcc-ar'
        self.vars['SHLINK']      = 'gcc'
        self.vars['RANLIB']      = 'gcc-ranlib'
        self.vars['STRIP']       = 'strip'

        # default flags
        self.vars['ASFLAGS']     = []
        self.vars['CFLAGS']      = []
        self.vars['CPPFLAGS']    = []
        self.vars['CXXFLAGS']    = []
        self.vars['LINKFLAGS']   = []
        self.vars['SHLINKFLAGS'] = []
        self.vars['CRGFLAGS']    = []
        self.vars['ARFLAGS']     = ['rc']

        # default paths
        self.vars['LIBDIR']      = 'build'
        self.vars['BUILDDIR']    = 'build'
        self.vars['RUSTBINS']    = 'build'
        self.vars['CPPPATH']     = []
        self.vars['LIBPATH']     = [self.vars['LIBDIR']]

    def clone(self):
        env = type(self)()
        env.cwd = self.cwd
        env.vars = copy.deepcopy(self.vars)
        return env

    def __getitem__(self, var: str):
        return self.vars[var]

    def __setitem__(self, var: str, value):
        self.vars[var] = value

    def add_flag(self, var: str, flag: str):
        self.add_flags(var, [flag])

    def add_flags(self, var: str, flags: list[str]):
        assert isinstance(self.vars[var], list)
        self.vars[var] += flags

    def remove_flag(self, var: str, flag: str):
        self.remove_flags(var, [flag])

    def remove_flags(self, var: str, flags: list[str]):
        for f in flags:
            assert isinstance(self.vars[var], list)
            if f in self.vars[var]:
                self.vars[var].remove(f)

    def sub_build(self, gen: Generator, dir: str):
        old_cwd = self.cwd.path
        self.cwd.path += '/' + dir

        mod_path = self.cwd.path[2:].replace('/', '.')
        b = importlib.import_module(mod_path + '.build')
        b.build(gen, self)

        self.cwd.path = old_cwd

    def glob(self, pattern: str, recursive: bool=False) -> list[SourcePath]:
        files = glob(self.cwd.path + '/' + pattern, recursive=recursive)
        return [SourcePath(f) for f in files]

    def install(self, gen: Generator, outdir: str, input: str, flags: str = '') -> str:
        return self.install_as(gen, outdir + '/' + os.path.basename(input), input, flags)

    def install_as(self, gen: Generator, out: str, input: str, flags: str = '') -> str:
        edge = BuildEdge(
            'install',
            outs = [out],
            ins = [SourcePath.new(self, input)],
            vars = {
                'instflags' : flags
            }
        )
        gen.add_build(edge)
        return out

    def strip(self, gen: Generator, out: str, input: str) -> BuildPath:
        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'strip',
            outs = [bin],
            ins = [SourcePath.new(self, input)],
            vars = {
                'strip' : self['STRIP']
            }
        )
        gen.add_build(edge)
        return bin

    def cpp(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        flags = ' '.join(self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'cpp',
            outs = [bin],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = {
                'cpp' : self['CPP'],
                'cppflags' : flags
            }
        )
        gen.add_build(edge)
        return bin

    def asm(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        flags = ' '.join(self['ASFLAGS'])
        return self._cc(gen, out, ins, flags)

    def cc(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        flags = ' '.join(self['CFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])
        return self._cc(gen, out, ins, flags)

    def _cc(self, gen: Generator, out: str, ins: list[str], flags: str) -> BuildPath:
        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cc',
            outs = [obj],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = {
                'cc' : self['CC'],
                'ccflags' : flags
            }
        )
        gen.add_build(edge)
        return obj

    def cxx(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        flags = ' '.join(self['CXXFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cxx',
            outs = [obj],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = {
                'cxx' : self['CXX'],
                'cxxflags' : flags
            }
        )
        gen.add_build(edge)
        return obj

    def objs(self, gen: Generator, ins: list[str]) -> list[BuildPath]:
        objs = []
        for i in ins:
            if i.endswith('.S') or i.endswith('.s'):
                objs.append(self.asm(gen, BuildPath.with_ending(self, i, '.o'), [i]))
            elif i.endswith('.c'):
                objs.append(self.cc(gen, BuildPath.with_ending(self, i, '.o'), [i]))
            elif i.endswith('.cc') or i.endswith('.cpp'):
                objs.append(self.cxx(gen, BuildPath.with_ending(self, i, '.o'), [i]))
            elif i.endswith('.o') or i.endswith('.a'):
                objs.append(BuildPath.new(self, i))
        return objs

    def static_lib(self, gen: Generator, out: str, ins: list[str], install: bool = True) -> BuildPath:
        flags = ' '.join(self['ARFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.a')
        edge = BuildEdge(
            'ar',
            outs = [lib],
            ins = self.objs(gen, ins),
            vars = {
                'ar' : self['AR'],
                'ranlib' : self['RANLIB'],
                'arflags' : flags
            }
        )
        gen.add_build(edge)
        # don't install it if the library is already in LIBDIR
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self['LIBDIR']):
            self.install(gen, self['LIBDIR'], lib)
        return lib

    def shared_lib(self, gen: Generator, out: str, ins: list[str], install: bool = True) -> BuildPath:
        flags = ' '.join(self['SHLINKFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.so')
        edge = BuildEdge(
            'shlink',
            outs = [lib],
            ins = self.objs(gen, ins),
            vars = {
                'shlink' : self['SHLINK'],
                'shlinkflags' : flags
            }
        )
        gen.add_build(edge)
        # don't install it if the library is already in LIBDIR
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self['LIBDIR']):
            self.install(gen, self['LIBDIR'], lib)
        return lib

    def c_exe(self, gen: Generator, out: str, ins: list[str],
              libs: list[str] = [], deps: list[str] = []) -> BuildPath:
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CC'])

    def cxx_exe(self, gen: Generator, out: str, ins: list[str],
                libs: list[str] = [], deps: list[str] = []) -> BuildPath:
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CXX'])

    def _c_cxx_exe(self, gen: Generator, out: str, ins: list[str],
                   libs: list[str], deps: list[str], linker: str) -> BuildPath:
        flags = ''
        if len(libs) > 0:
            flags += ' '.join(self['LINKFLAGS'])
            flags += ' ' + ' '.join(['-L' + d for d in self['LIBPATH']])
            flags += ' -Wl,--start-group'
            flags += ' ' + ' '.join(['-l' + l for l in libs])
            flags += ' -Wl,--end-group'

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'link',
            outs = [bin],
            ins = self.objs(gen, ins),
            deps = deps,
            pre_deps = libs,
            lib_path = self['LIBPATH'],
            vars = {
                'link' : linker,
                'linkflags' : flags
            }
        )
        gen.add_build(edge)
        return bin

    def rust_lib(self, gen: Generator, out: str, deps: list[str] = []) -> BuildPath:
        return self._rust(gen, 'lib' + out + '.a', deps, self['LIBDIR'])

    def rust_exe(self, gen: Generator, out: str, deps: list[str] = []) -> BuildPath:
        return self._rust(gen, out, deps, self['BUILDDIR'])

    def _rust(self, gen: Generator, out: str, deps: list[str], installDir) -> BuildPath:
        # determine destination based on flags
        btype = 'release' if '--release' in self['CRGFLAGS'] else 'debug'
        bin = BuildPath(self['RUSTBINS'] + '/' + btype + '/' + out)
        # make sure that cargo puts it there
        env = 'CARGO_TARGET_DIR="' + self['RUSTBINS'] + '"'

        edge = BuildEdge(
            'cargo',
            outs = [bin],
            ins = [],
            deps = deps,
            vars = {
                'dir' : self.cwd.path,
                'cargoflags' : 'build ' + ' '.join(self['CRGFLAGS']),
                'env' : env
            }
        )
        gen.add_build(edge)

        # don't install it if the binary is already in installDir
        if os.path.dirname(os.path.abspath(bin)) != os.path.abspath(installDir):
            self.install(gen, installDir, bin)
        return BuildPath(installDir + '/' + out)
