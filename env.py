import copy
from glob import glob
import importlib
import os

from path import BuildPath, SourcePath
from generator import BuildEdge, Generator


class Env:
    """
    An `Env` is a container for variables that are used to produce build edges for the `Generator`.

    The variables are tools (e.g., `CXX`), compiler flags (e.g., `CFLAGS`), and paths (e.g.,
    `CPPPATH`). These variables can be changed and, when their values are as desired, build edges
    can be produced based on them. In particular, `Env` can be cloned to change a variable for a
    particular build edge without influencing anything else.

    Furthermore, `Env` holds a current working directory (`Env.cur_dir`) which is used to specify
    the paths to input files relatively. The output files are put into the build directory, given by
    the environment variable `$NPBUILD`.

    An example usage of `Env` looks like the following:
    ```
    env = Env()
    gen = Generator()
    env['CXXFLAGS'] += ['-Wall', '-Wextra']
    env.cxx_exe(gen, out='hello', ins=['hello.cc'])
    gen.write_to_file()
    ```
    """

    class _Location:
        def __init__(self, path: str):
            self.path = path

    def __init__(self):
        """
        Creates a new `Env` with default settings.

        By default, the tools are set to the gcc and binutils toolchain (`CXX`=`g++`, `AR`=`gcc-ar`,
        etc.), compiler flags are empty, and paths are empty as well.
        """

        self._cwd = Env._Location('.')
        self._build_dir = os.environ.get('NPBUILD')
        self._vars = {}

        # default tools
        self._vars['CXX'] = 'g++'
        self._vars['CPP'] = 'cpp'
        self._vars['AS'] = 'gcc'
        self._vars['CC'] = 'gcc'
        self._vars['AR'] = 'gcc-ar'
        self._vars['SHLINK'] = 'gcc'
        self._vars['RANLIB'] = 'gcc-ranlib'
        self._vars['STRIP'] = 'strip'

        # default flags
        self._vars['ASFLAGS'] = []
        self._vars['CFLAGS'] = []
        self._vars['CPPFLAGS'] = []
        self._vars['CXXFLAGS'] = []
        self._vars['LINKFLAGS'] = []
        self._vars['SHLINKFLAGS'] = []
        self._vars['CRGFLAGS'] = []
        self._vars['ARFLAGS'] = ['rc']
        self._vars['INSTFLAGS'] = []

        # default paths
        self._vars['RUSTBINS'] = '.'
        self._vars['CPPPATH'] = []
        self._vars['LIBPATH'] = []

    def clone(self):
        """
        Clones this environment to produce an independently changable copy.

        The clone can be used to change the variables of the environment in order to prepare for a
        build edge with different settings without influencing other build edges.

        An example usage looks like the following:
        ```
        env['CFLAGS'] += ['-Wall', '-Wextra']

        foo_env = env.clone()
        foo_env.add_flag('CPPFLAGS', '-DMY_CONSTANT=42')
        foo_env.remove_flag('CFLAGS', '-Wextra')
        obj = foo_env.cc(gen, out='foo.o', ins=['foo.c'])

        env.c_exe(gen, out='hello', ins=['hello.c', obj])
        ```

        The example has a general environment with default settings and clones this environment to
        produce an object file that requires different settings to be built. Afterwards, the
        original environment is used to link the application.
        """

        env = type(self)()
        env._cwd = self._cwd
        env._vars = copy.deepcopy(self._vars)
        return env

    @property
    def cur_dir(self) -> str:
        """
        Returns the current directory where input files are expected
        """

        return self._cwd.path

    @property
    def build_dir(self) -> str:
        """
        Returns the build directory where all output files are placed (potentially in sub
        directories)
        """

        return self._build_dir

    def __getitem__(self, var: str):
        """
        Returns the value or the variable with given name

        Parameters
        ----------
        :param var: the variable name

        Returns
        -------
        The value of the variable
        """

        return self._vars[var]

    def __setitem__(self, var: str, value):
        """
        Sets the value or the variable with given name to `value`

        Parameters
        ----------
        :param var: the variable name
        :param value: the new value
        """

        self._vars[var] = value

    def add_flag(self, var: str, flag: str):
        """
        Adds a flag to the given flag variable

        This is a convenience method that is semantically equivalent to:
        ```
        self[var] += [flag]
        ```

        Note that this can only be used for variables of type `list[str]` such as `CFLAGS`.

        Parameters
        ----------
        :param var: the variable name
        :param flag: the flag to add
        """

        self.add_flags(var, [flag])

    def add_flags(self, var: str, flags: list[str]):
        """
        Adds flags to the given flag variable

        This is a convenience method that is semantically equivalent to:
        ```
        self[var] += flags
        ```

        Note that this can only be used for variables of type `list[str]` such as `CFLAGS`.

        Parameters
        ----------
        :param var: the variable name
        :param flags: a list of flags to add
        """

        assert isinstance(self._vars[var], list)
        self._vars[var] += flags

    def remove_flag(self, var: str, flag: str):
        """
        Removes the given flag from the given flag variable

        This is a convenience method that is semantically equivalent to:
        ```
        self[var].remove(flag)
        ```

        Note that this can only be used for variables of type `list[str]` such as `CFLAGS`.

        Parameters
        ----------
        :param var: the variable name
        :param flag: the flag to remove
        """

        self.remove_flags(var, [flag])

    def remove_flags(self, var: str, flags: list[str]):
        """
        Removes the given flags from the given flag variable

        This is a convenience method that is semantically equivalent to:
        ```
        for flag in flags:
            self[var].remove(flag)
        ```

        Note that this can only be used for variables of type `list[str]` such as `CFLAGS`.

        Parameters
        ----------
        :param var: the variable name
        :param flags: the flags to remove
        """

        for f in flags:
            assert isinstance(self._vars[var], list)
            if f in self._vars[var]:
                self._vars[var].remove(f)

    def sub_build(self, gen: Generator, dir: str):
        """
        Calls the build.py in the given subdirectory

        In a project with multiple files to build (libraries, executables, etc.), it makes sense to
        organize them into multiple directories. This method is used to run the `build.py` in a
        subdirectory and thus add the rules and build edges produced there to the generator. Before
        running the `build.py`, the current directory (`Env.cur_dir`) will be changed to the
        subdirectory. This allows the `build.py` in the subdirectory to use paths relative to its
        own directory. Of course, `Env.sub_build` can be nested arbitrarily deep.

        The `build.py` files in the subdirectory are expected to contain a function `build` with the
        generator and environment as arguments. This will be called by `Env.sub_build`.

        For example, the `build.py` in the root directory could do the following:
        ```
        env.sub_build(gen, 'sub')
        env.c_exe(gen, out='hello', ins=['hello.c'], libs=['sub'])
        gen.write_to_file()
        ```
        And the `build.py` in the subdirectory `sub`:
        ```
        def build(gen, env):
            env.static_lib(gen, out='sub', ins=['sub.c'])
        ```

        This example would produce `libsub.a` in the subdirectory and use it to produce the `hello`
        executable in the root directory.
        """

        old_cwd = self.cur_dir
        self._cwd.path += '/' + dir

        mod_path = self.cur_dir[2:].replace('/', '.')
        b = importlib.import_module(mod_path + '.build')
        b.build(gen, self)

        self._cwd.path = old_cwd

    def glob(self, pattern: str, recursive: bool = False) -> list[SourcePath]:
        # TODO store these globs into a file and use exactly these for find to determine whether
        # something has changed
        files = glob(self.cur_dir + '/' + pattern, recursive=recursive)
        return [SourcePath(f) for f in files]

    def install(self, gen: Generator, outdir: str, input: str) -> str:
        """
        Installs the given input file into the given output directory

        Parameters
        ----------
        :param gen: the generator
        :param outdir: the output directory
        :param input: the input file

        Returns
        -------
        The path of the installed file
        """

        return self.install_as(gen, outdir + '/' + os.path.basename(input), input)

    def install_as(self, gen: Generator, out: str, input: str) -> str:
        """
        Installs the given input file into the given output file

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param input: the input file

        Variables
        ---------
        :param `INSTFLAGS`: the flags (e.g., ['--mode=0644'])

        Returns
        -------
        The path of the installed file
        """

        flags = ' '.join(self['INSTFLAGS'])
        edge = BuildEdge(
            'install',
            outs=[out],
            ins=[SourcePath.new(self, input)],
            vars={
                'instflags': flags
            }
        )
        gen.add_build(edge)
        return out

    def strip(self, gen: Generator, out: str, input: str) -> BuildPath:
        """
        Strips the symbols from the given input file

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param input: the input file

        Variables
        ---------
        :param `STRIP`: the tool name (e.g., 'arm-none-eabi-strip')

        Returns
        -------

        A `BuildPath` to the stripped file
        """

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'strip',
            outs=[bin],
            ins=[SourcePath.new(self, input)],
            vars={
                'strip': self['STRIP']
            }
        )
        gen.add_build(edge)
        return bin

    def cpp(self, gen: Generator, out: str, input: str) -> BuildPath:
        """
        Runs the C preprocessor on the given input file

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param input: the input file

        Variables
        ---------
        :param `CPP`: the tool name (e.g., 'arm-none-eabi-cpp')
        :param `CPPFLAGS`: the flags (e.g., ['-DFOO=1'])
        :param `CPPPATH`: the include paths (e.g., ['include'])

        Returns
        -------
        A `BuildPath` to the output file
        """

        flags = ' '.join(self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'cpp',
            outs=[bin],
            ins=[SourcePath.new(self, input)],
            vars={
                'cpp': self['CPP'],
                'cppflags': flags
            }
        )
        gen.add_build(edge)
        return bin

    def asm(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        """
        Runs the assember on the given input files

        Note that this method assumes that the C compiler (like gcc) can be used for this purpose.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files

        Variables
        ---------
        :param `CC`: the tool name (e.g., 'gcc')
        :param `ASFLAGS`: the flags (e.g., ['-Wa,--32'])

        Returns
        -------
        A `BuildPath` to the output file
        """

        flags = ' '.join(self['ASFLAGS'])
        return self._cc(gen, out, ins, flags)

    def cc(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        """
        Runs the C compiler on the given input files

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files

        Variables
        ---------
        :param `CC`: the tool name (e.g., 'gcc')
        :param `CFLAGS`: the flags (e.g., ['-Wall'])
        :param `CPPFLAGS`: the preprocessor flags (e.g., ['-DFOO=1'])
        :param `CPPPATH`: the include paths (e.g., ['include'])

        Returns
        -------
        A `BuildPath` to the output file
        """

        flags = ' '.join(self['CFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])
        return self._cc(gen, out, ins, flags)

    def _cc(self, gen: Generator, out: str, ins: list[str], flags: str) -> BuildPath:
        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cc',
            outs=[obj],
            ins=[SourcePath.new(self, i) for i in ins],
            vars={
                'cc': self['CC'],
                'ccflags': flags
            }
        )
        gen.add_build(edge)
        return obj

    def cxx(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        """
        Runs the C++ compiler on the given input files

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files

        Variables
        ---------
        :param `CXX`: the tool name (e.g., 'g++')
        :param `CXXFLAGS`: the flags (e.g., ['-Wall'])
        :param `CPPFLAGS`: the preprocessor flags (e.g., ['-DFOO=1'])
        :param `CPPPATH`: the include paths (e.g., ['include'])

        Returns
        -------
        A `BuildPath` to the output file
        """

        flags = ' '.join(self['CXXFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])

        obj = BuildPath.new(self, out)
        edge = BuildEdge(
            'cxx',
            outs=[obj],
            ins=[SourcePath.new(self, i) for i in ins],
            vars={
                'cxx': self['CXX'],
                'cxxflags': flags
            }
        )
        gen.add_build(edge)
        return obj

    def objs(self, gen: Generator, ins: list[str]) -> list[BuildPath]:
        """
        Produces object files for the given input files

        This method will call `Env.asm`, `Env.cc`, or `Env.cxx` to build the input file, depending
        on the file extension. Object files or libraries are simply appended to list of output
        files.

        Parameters
        ----------
        :param gen: the generator
        :param ins: the list of input files

        Returns
        -------
        A list of `BuildPath`s to the object files
        """

        objs = []
        for i in ins:
            if i.endswith('.S') or i.endswith('.s'):
                objs.append(self.asm(gen, BuildPath.with_file_ext(self, i, 'o'), [i]))
            elif i.endswith('.c'):
                objs.append(self.cc(gen, BuildPath.with_file_ext(self, i, 'o'), [i]))
            elif i.endswith('.cc') or i.endswith('.cpp'):
                objs.append(self.cxx(gen, BuildPath.with_file_ext(self, i, 'o'), [i]))
            elif i.endswith('.o') or i.endswith('.a') or i.endswith('.so'):
                objs.append(BuildPath.new(self, i))
        return objs

    def static_lib(self, gen: Generator, out: str, ins: list[str],
                   install: bool = True) -> BuildPath:
        """
        Produces the static library `"lib" + out + ".a"` from given input files

        The input files can be file type that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param install: whether the library should be installed in the default library folder
            (`Env.build_path`)

        Variables
        ---------
        :param `AR`: the tool name for archiving (e.g., 'gcc-ar')
        :param `RANLIB`: the tool name for index generation (e.g., 'gcc-ranlib')
        :param `ARFLAGS`: the flags

        Returns
        -------
        The `BuildPath` to the produced static library
        """

        flags = ' '.join(self['ARFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.a')
        edge = BuildEdge(
            'ar',
            outs=[lib],
            ins=self.objs(gen, ins),
            vars={
                'ar': self['AR'],
                'ranlib': self['RANLIB'],
                'arflags': flags
            }
        )
        gen.add_build(edge)
        # don't install it if the library is already in self.build_dir
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self.build_dir):
            self.install(gen, self.build_dir, lib)
        return lib

    def shared_lib(self, gen: Generator, out: str, ins: list[str],
                   install: bool = True) -> BuildPath:
        """
        Produces the shared library `"lib" + out + ".so"` from given input files

        The input files can be file type that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param install: whether the library should be installed in the default library folder
            (`Env.build_path`)

        Variables
        ---------
        :param `SHLINK`: the tool name to create the shared library (e.g., 'gcc')
        :param `SHLINKFLAGS`: the flags (e.g., ['-march=rv64imafdc'])

        Returns
        -------
        The `BuildPath` to the produced shared library
        """

        flags = ' '.join(self['SHLINKFLAGS'])
        lib = BuildPath.new(self, 'lib' + out + '.so')
        edge = BuildEdge(
            'shlink',
            outs=[lib],
            ins=self.objs(gen, ins),
            vars={
                'shlink': self['SHLINK'],
                'shlinkflags': flags
            }
        )
        gen.add_build(edge)
        # don't install it if the library is already in self.build_dir
        if install and os.path.dirname(os.path.abspath(lib)) != os.path.abspath(self.build_dir):
            self.install(gen, self.build_dir, lib)
        return lib

    def c_exe(self, gen: Generator, out: str, ins: list[str],
              libs: list[str] = [], deps: list[str] = []) -> BuildPath:
        """
        Produces a C executable from given input files

        The input files can be file type that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param libs: the list of libraries that the executable should be linked against
        :param deps: the additional list of dependencies

        Variables
        ---------
        :param `CC`: the tool name (e.g., 'gcc')
        :param `LINKFLAGS`: the flags (e.g., ['-march=rv64imafdc'])
        :param `LIBPATH`: the paths to search libraries in (e.g., ['lib'])

        Returns
        -------
        The `BuildPath` to the produced executable
        """

        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CC'])

    def cxx_exe(self, gen: Generator, out: str, ins: list[str],
                libs: list[str] = [], deps: list[str] = []) -> BuildPath:
        """
        Produces a C++ executable from given input files

        The input files can be file type that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param libs: the list of libraries that the executable should be linked against
        :param deps: the additional list of dependencies

        Variables
        ---------
        :param `CXX`: the tool name (e.g., 'g++')
        :param `LINKFLAGS`: the flags (e.g., ['-march=rv64imafdc'])
        :param `LIBPATH`: the paths to search libraries in (e.g., ['lib'])

        Returns
        -------
        The `BuildPath` to the produced executable
        """

        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CXX'])

    def _c_cxx_exe(self, gen: Generator, out: str, ins: list[str],
                   libs: list[str], deps: list[str], linker: str) -> BuildPath:
        flags = ''
        lib_path = [self.build_dir] + self['LIBPATH']
        if len(libs) > 0:
            flags += ' '.join(self['LINKFLAGS'])
            flags += ' ' + ' '.join(['-L' + dir for dir in lib_path])
            flags += ' -Wl,--start-group'
            flags += ' ' + ' '.join(['-l' + lib for lib in libs])
            flags += ' -Wl,--end-group'

        bin = BuildPath.new(self, out)
        edge = BuildEdge(
            'link',
            outs=[bin],
            ins=self.objs(gen, ins),
            deps=deps,
            libs=libs,
            lib_path=lib_path,
            vars={
                'link': linker,
                'linkflags': flags
            }
        )
        gen.add_build(edge)
        return bin

    def rust_lib(self, gen: Generator, out: str, deps: list[str] = []) -> BuildPath:
        """
        Produces a Rust library from given input files

        This method runs `cargo` in the current directory and therefore expects a `Cargo.toml` that
        produces a static Rust library. `CARGO_TARGET_DIR` will be set according to `Env.build_dir`
        and `RUSTBINS`. The produced static library will be installed to the default library folder
        (`Env.build_path`).

        Note: if `deps` is empty, this build edge will always be rebuilt to let `cargo` determine
        the required actions.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param deps: the additional list of dependencies

        Variables
        ---------
        :param `CRGFLAGS`: the flags (e.g., ['--release'])
        :param `RUSTBINS`: an optional subdirectory in `Env.build_dir` for Rust outputs

        Returns
        -------
        The `BuildPath` to the produced static library
        """

        return self._rust(gen, 'lib' + out + '.a', deps, self.build_dir)

    def rust_exe(self, gen: Generator, out: str, deps: list[str] = []) -> BuildPath:
        """
        Produces a Rust executable from given input files

        This method runs `cargo` in the current directory and therefore expects a `Cargo.toml` that
        produces a binary. `CARGO_TARGET_DIR` will be set according to `Env.build_dir` and
        `RUSTBINS`. The produced executable will be installed to the build directory
        (`Env.build_path`).

        Note: if `deps` is empty, this build edge will always be rebuilt to let `cargo` determine
        the required actions.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param deps: the additional list of dependencies

        Variables
        ---------
        :param `CRGFLAGS`: the flags (e.g., ['--release'])
        :param `RUSTBINS`: an optional subdirectory in `Env.build_dir` for Rust outputs

        Returns
        -------
        The `BuildPath` to the produced executable
        """

        return self._rust(gen, out, deps, self.build_dir)

    def _rust(self, gen: Generator, out: str, deps: list[str], installDir) -> BuildPath:
        # determine destination based on flags
        btype = 'release' if '--release' in self['CRGFLAGS'] else 'debug'
        bin = BuildPath.new(self, self['RUSTBINS'] + '/' + btype + '/' + out)
        # make sure that cargo puts it there
        env = 'CARGO_TARGET_DIR="' + self.build_dir + '/' + self['RUSTBINS'] + '"'

        edge = BuildEdge(
            'cargo',
            outs=[bin],
            ins=[],
            deps=deps,
            vars={
                'dir': self.cur_dir,
                'cargoflags': 'build ' + ' '.join(self['CRGFLAGS']),
                'env': env
            }
        )
        gen.add_build(edge)

        # don't install it if the binary is already in installDir
        if os.path.dirname(os.path.abspath(bin)) != os.path.abspath(installDir):
            self.install(gen, installDir, bin)
        return BuildPath(installDir + '/' + out)
