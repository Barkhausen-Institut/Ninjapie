import copy
from glob import glob
import importlib
import os

from ninjapie.path import BuildPath, SourcePath
from ninjapie.generator import BuildEdge, Generator


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
    >>> env = Env()
    ... gen = Generator()
    ... env['CXXFLAGS'] += ['-Wall', '-Wextra']
    ... env.cxx_exe(gen, out='hello', ins=['hello.cc'])
    ... gen.write_to_file()
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

        self._id = 1
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
        self._vars['CARGO'] = 'cargo'

        # default flags
        self._vars['ASFLAGS'] = []
        self._vars['CFLAGS'] = []
        self._vars['CPPFLAGS'] = []
        self._vars['CXXFLAGS'] = []
        self._vars['LINKFLAGS'] = []
        self._vars['SHLINKFLAGS'] = []
        self._vars['ARFLAGS'] = []
        self._vars['INSTFLAGS'] = []

        # default paths
        self._vars['CPPPATH'] = []
        self._vars['LIBPATH'] = []

        # default rust settings
        self._vars['RUSTBINS'] = '.'
        self._vars['CRGFLAGS'] = []
        self._vars['CRGENV'] = {}

    def clone(self):
        """
        Clones this environment to produce an independently changable copy.

        The clone can be used to change the variables of the environment in order to prepare for a
        build edge with different settings without influencing other build edges.

        An example usage looks like the following:
        >>> env['CFLAGS'] += ['-Wall', '-Wextra']
        ...
        ... foo_env = env.clone()
        ... foo_env.add_flag('CPPFLAGS', '-DMY_CONSTANT=42')
        ... foo_env.remove_flag('CFLAGS', '-Wextra')
        ... obj = foo_env.cc(gen, out='foo.o', ins=['foo.c'])
        ...
        ... env.c_exe(gen, out='hello', ins=['hello.c', obj])

        The example has a general environment with default settings and clones this environment to
        produce an object file that requires different settings to be built. Afterwards, the
        original environment is used to link the application.
        """

        env = type(self)()
        env._id = self._id + 1
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
        >>> self[var] += [flag]

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
        >>> self[var] += flags

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
        >>> self[var].remove(flag)

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
        >>> for flag in flags:
        ...     self[var].remove(flag)

        Note that this can only be used for variables of type `list[str]` such as `CFLAGS`.

        Parameters
        ----------
        :param var: the variable name
        :param flags: the flags to remove
        """

        for flag in flags:
            assert isinstance(self._vars[var], list)
            if flag in self._vars[var]:
                self._vars[var].remove(flag)

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
        >>> env.sub_build(gen, 'sub')
        ... env.c_exe(gen, out='hello', ins=['hello.c'], libs=['sub'])
        ... gen.write_to_file()
        And the `build.py` in the subdirectory `sub`:
        >>> def build(gen, env):
        ...     env.static_lib(gen, out='sub', ins=['sub.c'])

        This example would produce `libsub.a` in the subdirectory and use it to produce the `hello`
        executable in the root directory.

        Parameters
        ----------
        :param gen: the generator
        :param dir: the subdirectory to enter

        Returns
        -------
        The return value of the build function in the subdirectory
        """

        old_cwd = self.cur_dir
        self._cwd.path += '/' + dir

        gen._add_build_file(self.cur_dir + '/build.py')

        mod_path = self.cur_dir[2:].replace('/', '.')
        sub = importlib.import_module(mod_path + '.build')
        res = sub.build(gen, self)

        self._cwd.path = old_cwd
        return res

    def glob(self, gen: Generator, pattern: str) -> list[SourcePath]:
        """
        Produces a list of files that match the given pattern

        The pattern uses the same syntax as the Python function `glob.glob`. For example, '*.c'
        produces a list of all C files in the current directory. Since the `recursive` argument to
        `glob.glob` is always set to true, '**/*.c' would produce a list of all C files in the
        current directory or subdirectories.

        Note that globbing has the side effect that the required build steps might change on added
        or removed files. For that reason, Ninjapie records the glob patterns and regenerates the
        ninja build file whenever any file is added or removed. In other words, using `Env.glob` is
        a trade-off between more convenience and faster builds, because Ninjapie needs to perform
        additional checks for globs. Note that this also means that *only* this function should be
        used for globbing, because all other ways bypass Ninjapie and therefore lead to potentially
        outdated ninja build files.

        Parameters
        ----------
        :param gen: the generator
        :param pattern: the pattern for globbing

        Returns
        -------
        The list of found files as `SourcePath` objects
        """

        pat = SourcePath.new(self, pattern)
        gen._add_glob(pat)
        files = glob(pat, recursive=True)
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
        :param `CPPFLAGS`: the preprocessor flags (e.g., ['-DFOO=1'])
        :param `CPPPATH`: the include paths (e.g., ['include'])

        Returns
        -------
        A `BuildPath` to the output file
        """

        flags = ' '.join(self['ASFLAGS'] + self['CPPFLAGS'])
        flags += ' ' + ' '.join(['-I' + i for i in self['CPPPATH']])
        return self._cc(gen, out, ins, flags)

    def cc(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:  # pylint: disable=C0103
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

        # add a per-environment suffix to allow users to build the same files in different
        # environments without interference
        suffix = str(self._id) + '.o'
        objs = []
        for i in ins:
            if i.endswith('.S') or i.endswith('.s'):
                objs.append(self.asm(gen, BuildPath.with_file_ext(self, i, suffix), [i]))
            elif i.endswith('.c'):
                objs.append(self.cc(gen, BuildPath.with_file_ext(self, i, suffix), [i]))
            elif i.endswith('.cc') or i.endswith('.cpp'):
                objs.append(self.cxx(gen, BuildPath.with_file_ext(self, i, suffix), [i]))
            elif i.endswith('.o') or i.endswith('.a') or i.endswith('.so'):
                objs.append(BuildPath.new(self, i))
        return objs

    def static_lib(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        """
        Produces the static library `"lib" + out + ".a"` from given input files

        The input files can be all file types that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files

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
        return lib

    def shared_lib(self, gen: Generator, out: str, ins: list[str]) -> BuildPath:
        """
        Produces the shared library `"lib" + out + ".so"` from given input files

        The input files can be all file types that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files

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
        return lib

    def c_exe(self, gen: Generator, out: str, ins: list[str],
              libs: list[str] = None, deps: list[str] = None) -> BuildPath:
        """
        Produces a C executable from given input files

        The input files can be all file types that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param libs: the list of library names that the executable should be linked against
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

        libs = [] if libs is None else libs
        deps = [] if deps is None else deps
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CC'])

    def cxx_exe(self, gen: Generator, out: str, ins: list[str],
                libs: list[str] = None, deps: list[str] = None) -> BuildPath:
        """
        Produces a C++ executable from given input files

        The input files can be all file types that `Env.objs` supports.

        Parameters
        ----------
        :param gen: the generator
        :param out: the output file
        :param ins: the list of input files
        :param libs: the list of library names that the executable should be linked against
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

        libs = [] if libs is None else libs
        deps = [] if deps is None else deps
        return self._c_cxx_exe(gen, out, ins, libs, deps, self['CXX'])

    def _c_cxx_exe(self, gen: Generator, out: str, ins: list[str],
                   libs: list[str], deps: list[str], linker: str) -> BuildPath:
        flags = ''
        if len(libs) > 0:
            flags += ' '.join(self['LINKFLAGS'])
            flags += ' ' + ' '.join(['-L' + dir for dir in self['LIBPATH']])
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
            lib_path=self['LIBPATH'],
            vars={
                'link': linker,
                'linkflags': flags
            }
        )
        gen.add_build(edge)
        return bin

    def rust_lib(self, gen: Generator, out: str, deps: list[str] = None) -> BuildPath:
        """
        Produces a Rust library

        This method runs `cargo` in the current directory and therefore expects a `Cargo.toml` that
        produces a static Rust library. The `--target-dir` argument will be pass to cargo according
        to `Env.build_dir` and `RUSTBINS`. The location of the produced file will be determined by
        the `--target` and `--release` arguments in `CRGFLAGS`, if present. You can also use
        `CRGENV` to provide additional environment variables to cargo.

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
        :param `CRGENV`: additional environment variables

        Returns
        -------
        The `BuildPath` to the produced static library
        """

        deps = [] if deps is None else deps
        return self.rust(gen, ['lib' + out + '.a'], deps)[0]

    def rust_exe(self, gen: Generator, out: str, deps: list[str] = None) -> BuildPath:
        """
        Produces a Rust executable

        This method runs `cargo` in the current directory and therefore expects a `Cargo.toml` that
        produces a binary. The `--target-dir` argument will be pass to cargo according to
        `Env.build_dir` and `RUSTBINS`. The location of the produced file will be determined by the
        `--target` and `--release` arguments in `CRGFLAGS`, if present. You can also use `CRGENV` to
        provide additional environment variables to cargo.

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
        :param `CRGENV`: additional environment variables

        Returns
        -------
        The `BuildPath` to the produced executable
        """

        deps = [] if deps is None else deps
        return self.rust(gen, [out], deps)[0]

    def rust(self, gen: Generator, outs: list[str], deps: list[str]) -> [BuildPath]:
        """
        Produces multiple Rust libraries or executables

        This method runs `cargo` in the current directory and therefore expects a `Cargo.toml`. The
        `--target-dir` argument will be pass to cargo according to `Env.build_dir` and `RUSTBINS`.
        The location of the produced files will be determined by the `--target` and `--release`
        arguments in `CRGFLAGS`, if present. You can also use `CRGENV` to provide additional
        environment variables to cargo.

        Note: if `deps` is empty, this build edge will always be rebuilt to let `cargo` determine
        the required actions.

        Parameters
        ----------
        :param gen: the generator
        :param outs: the output files
        :param deps: the additional list of dependencies

        Variables
        ---------
        :param `CRGFLAGS`: the flags (e.g., ['--release'])
        :param `RUSTBINS`: an optional subdirectory in `Env.build_dir` for Rust outputs
        :param `CRGENV`: additional environment variables

        Returns
        -------
        A list of `BuildPath`s to the produced files
        """

        # determine whether cargo puts the output in a target-specific directory
        target_dir = ''
        try:
            idx = self['CRGFLAGS'].index('--target')
            target_dir = self['CRGFLAGS'][idx + 1] + '/'
        except ValueError:
            pass

        # determine destination directory
        btype = 'release' if '--release' in self['CRGFLAGS'] else 'debug'
        dest_dir = BuildPath(self.build_dir + '/' + self['RUSTBINS'] + '/' + target_dir + btype)
        out_paths = [BuildPath(dest_dir + '/' + o) for o in outs]

        flags = ' '.join(self['CRGFLAGS'])
        # make sure that cargo puts it there
        flags += ' --target-dir "' + os.path.abspath(self.build_dir + '/' + self['RUSTBINS']) + '"'

        # build environment variables
        vars_str = ''
        for key, value in self['CRGENV'].items():
            vars_str += ' ' + key + '="' + value + '"'

        edge = BuildEdge(
            'cargo',
            outs=out_paths,
            ins=[],
            deps=deps,
            vars={
                'cargo': self['CARGO'],
                'dir': self.cur_dir,
                'cargoflags': 'build ' + flags,
                'env': vars_str
            }
        )
        gen.add_build(edge)
        return out_paths
