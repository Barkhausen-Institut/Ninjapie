import copy
from glob import glob
import importlib
import os

from path import BuildPath, SourcePath
from generator import BuildEdge

class Location:
    def __init__(self, path):
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

    def __getitem__(self, var):
        return self.vars[var]

    def __setitem__(self, var, value):
        self.vars[var] = value

    def add_flag(self, var, flag):
        self.add_flags(var, [flag])

    def add_flags(self, var, flags):
        self.vars[var] += flags

    def remove_flag(self, var, flag):
        self.remove_flags(var, [flag])

    def remove_flags(self, var, flags):
        for f in flags:
            if f in self.vars[var]:
                self.vars[var].remove(f)

    def sub_build(self, gen, dir):
        old_cwd = self.cwd.path
        self.cwd.path += '/' + dir

        mod_path = self.cwd.path[2:].replace('/', '.')
        b = importlib.import_module(mod_path + '.build')
        b.build(gen, self)

        self.cwd.path = old_cwd

    def glob(self, pattern, recursive=False):
        files = glob(self.cwd.path + '/' + pattern, recursive=recursive)
        return [SourcePath(f) for f in files]

    def install(self, gen, outdir, input, flags = ''):
        return self.install_as(gen, outdir + '/' + os.path.basename(input), input, flags)

    def install_as(self, gen, out, input, flags = ''):
        edge = BuildEdge(
            'install',
            outs = [out],
            ins = [SourcePath.new(self, input)],
            vars = { 'instflags' : flags }
        )
        gen.add_build(edge)
        return out

    def strip(self, gen, out, input):
        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'strip',
            outs = [bin],
            ins = [SourcePath.new(self, input)],
            vars = { 'strip' : self['STRIP'] }
        )
        gen.add_build(edge)
        return bin

    def cpp(self, gen, out, ins):
        flags = ' '.join(self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'cpp',
            outs = [bin],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = { 'cpp' : self['CPP'], 'cppflags' : flags }
        )
        gen.add_build(edge)
        return bin

    def cc(self, gen, out, ins, flags = []):
        flags = ' '.join(self['CFLAGS'] + self['CPPFLAGS'] + flags)
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cc',
            outs = [obj],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = { 'cc' : self['CC'], 'ccflags' : flags }
        )
        gen.add_build(edge)
        return obj

    def asm(self, gen, out, ins):
        return self.cc(gen, out, ins, flags = self['ASFLAGS'])

    def cxx(self, gen, out, ins):
        flags = ' '.join(self['CXXFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cxx',
            outs = [obj],
            ins = [SourcePath.new(self, i) for i in ins],
            vars = { 'cxx' : self['CXX'], 'cxxflags' : flags }
        )
        gen.add_build(edge)
        return obj

    def objs(self, gen, ins):
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

    def static_lib(self, gen, out, ins, install = True):
        flags = ' '.join(self['ARFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.a')
        edge = BuildEdge(
            'ar',
            outs = [lib],
            ins = self.objs(gen, ins),
            vars = { 'ar' : self['AR'], 'ranlib' : self['RANLIB'], 'arflags' : flags }
        )
        gen.add_build(edge)
        # don't install it if the library is already in LIBDIR
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self['LIBDIR']):
            self.install(gen, self['LIBDIR'], lib)
        return lib

    def shared_lib(self, gen, out, ins, install = True):
        flags = ' '.join(self['SHLINKFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.so')
        edge = BuildEdge(
            'shlink',
            outs = [lib],
            ins = self.objs(gen, ins),
            vars = { 'shlink' : self['SHLINK'], 'shlinkflags' : flags }
        )
        gen.add_build(edge)
        # don't install it if the library is already in LIBDIR
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self['LIBDIR']):
            self.install(gen, self['LIBDIR'], lib)
        return lib

    def c_exe(self, gen, out, ins, libs = [], deps = []):
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CC'])

    def cxx_exe(self, gen, out, ins, libs = [], deps = []):
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CXX'])

    def _c_cxx_exe(self, gen, out, ins, libs, deps, linker):
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
            vars = { 'link' : linker, 'linkflags' : flags }
        )
        gen.add_build(edge)
        return bin

    def cargo(self, gen, out, cmd = 'build', deps = []):
        bin = BuildPath(self['RUSTBINS'] + '/' + out)
        deps += glob(self.cwd.path + '/**/*.rs', recursive=True)
        deps += [SourcePath.new(self, 'Cargo.toml')]
        edge = BuildEdge(
            'cargo',
            outs = [bin],
            ins = [],
            deps = deps,
            vars = {
                'dir' : self.cwd.path,
                'cargoflags' : cmd + ' ' + ' '.join(self['CRGFLAGS']),
            }
        )
        gen.add_build(edge)
        return bin
