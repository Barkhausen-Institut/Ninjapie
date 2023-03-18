import copy
from glob import glob
import importlib
import os
import subprocess

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
        self.vars['CXX']        = 'g++'
        self.vars['CPP']        = 'cpp'
        self.vars['AS']         = 'gcc'
        self.vars['CC']         = 'gcc'
        self.vars['AR']         = 'gcc-ar'
        self.vars['RANLIB']     = 'gcc-ranlib'
        self.vars['STRIP']      = 'strip'

        # default flags
        self.vars['ASFLAGS']    = []
        self.vars['CFLAGS']     = []
        self.vars['CPPFLAGS']   = []
        self.vars['CXXFLAGS']   = []
        self.vars['LINKFLAGS']  = []
        self.vars['CRGFLAGS']   = []
        self.vars['ARFLAGS']    = ['rc']

        # default paths
        self.vars['CPPPATH']    = []
        self.vars['LIBPATH']    = []
        self.vars['BUILDDIR']   = 'build'
        self.vars['RUSTBINS']   = 'build'

    def __getitem__(self, key):
        return self.vars[key]

    def __setitem__(self, key, value):
        self.vars[key] = value

    def remove_flag(self, flags, name):
        if name in self.vars[flags]:
            self.vars[flags].remove(name)

    def sub_build(self, gen, dir):
        old_cwd = self.cwd.path
        self.cwd.path += '/' + dir

        mod_path = self.cwd.path[2:].replace('/', '.')
        b = importlib.import_module(mod_path + '.build')
        b.build(gen, self)

        self.cwd.path = old_cwd

    def try_execute(self, cmd):
        return subprocess.getstatusoutput(cmd)[0] == 0

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
        edge = BuildEdge(
            'strip',
            outs = [out],
            ins = [SourcePath.new(self, input)],
        )
        gen.add_build(edge)
        return out

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

    def c_exe(self, gen, out, ins, libs = [], deps = []):
        return self._c_cxx_exe(gen, out, ins, linker = self['CC'], libs = libs, deps = deps)

    def cxx_exe(self, gen, out, ins, libs = [], deps = []):
        return self._c_cxx_exe(gen, out, ins, linker = self['CXX'], libs = libs, deps = deps)

    def _c_cxx_exe(self, gen, out, ins, linker, libs = [], deps = []):
        flags = ' '.join(self['LINKFLAGS'])
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

    def static_lib(self, gen, out, ins):
        flags = ' '.join(self['ARFLAGS'])
        lib = BuildPath.new(self, out + '.a')
        edge = BuildEdge(
            'ar',
            outs = [lib],
            ins = self.objs(gen, ins),
            vars = { 'ar' : self['AR'], 'ranlib' : self['RANLIB'], 'arflags' : flags }
        )
        gen.add_build(edge)
        return lib

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
