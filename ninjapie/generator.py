import os
import re
import traceback
from glob import glob


class Rule:
    """
    Represents a rule in the ninja build files.

    The primary properties of a rule are the command to execute and a description. Both the command
    and the description can contain variables, whose values will later be set by each `BuildEdge`
    that references the rule. The description is displayed during the build for information
    purposes.
    """

    def __init__(self, cmd: str, desc: str, deps: str = '', depfile: str = '',
                 generator: str = '', pool: str = '', restat: bool = False):
        """
        Creates a new rule

        Parameters
        ----------
        :param cmd: the command to execute
        :param desc: the description for the command (for information purposes)
        :param deps: either empty, 'gcc' or 'msvc'. The latter specify special dependency processing
            (header files).
        :param depfile: if not empty, a file in Makefile syntax that contains extra dependencies.
            This can be used for the file gcc generates with the `-MD` argument.
        :param generator: if not empty, specifies that this rule is used to re-invoke the generator
            program. See [Ninja manual](https://ninja-build.org/manual.html#ref_rule) for more
            detail.
        :param pool: if not empty, the name of the pool to use. See [Ninja
            manual](https://ninja-build.org/manual.html#ref_pool).
        :param restat: if `True`, causes Ninja to re-stat the command's outputs after execution of
            the command. Each output whose modification time the command did not change will be
            treated as though it had never needed to be built. This may cause the output's reverse
            dependencies to be removed from the list of pending build actions.
        """

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
        """
        Writes this rule to the given file object

        Parameters
        ----------
        :param name: the name of the rule
        :param file: the file object
        """

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
    """
    A build edge specifies that given output files are produced from given input files using a
    specific rule.

    A build edge therefore references a specific rule and assigns values to the variables defined
    for the rule. Most importantly, a rule has one or more output files and one or more input files.
    Whenever one of the input files changes, the command of the rule will be invoked to reproduce
    the output files. Additional dependencies can be specified to also trigger a rebuild.
    """

    def __init__(self, rule: str, outs: list[str], ins: list[str], deps: list[str] = None,
                 vars: dict[str, str] = None, libs: list[str] = None, lib_path: list[str] = None):
        """
        Creates a new build edge.

        Parameters
        ----------
        :param rule: the name of the rule (needs to exist in the `Generator`)
        :param outs: a list of paths that are produced as outputs when executing the command
        :param ins: a list of paths that are taken as inputs by the command
        :param deps: an optional list of paths with additional dependencies
        :param vars: an optional list with values for additional variables used in the rule
        :param libs: when producing executables, a list of library names that is linked against
        :param lib_path: when producing executables, a list of paths to search the libraries in
        """

        assert len(outs) > 0, "The list of output files cannot be empty"

        deps = [] if deps is None else deps
        vars = {} if vars is None else vars
        libs = [] if libs is None else libs
        lib_path = [] if lib_path is None else lib_path

        self.calltrace = None
        self.rule = rule
        self.outs = outs
        self.ins = ins
        # copy the dependencies, because we want to alter them for this specific BuildEdge later
        self.deps = deps.copy()
        # without inputs and dependencies, we always want to rebuild it
        if self.rule != 'phony' and len(self.ins) == 0 and len(self.deps) == 0:
            self.deps = ['always']
        self.libs = libs
        self.lib_path = lib_path
        self.vars = vars

    def _write_to_file(self, defaults: dict[str, str], file):
        """
        Writes this build edge to the given file object

        Parameters
        ----------
        :param defaults: a dictionary with default values. Only if a variable has not the default
            value, it will be specified for the build edge.
        :param file: the file object
        """

        file.write('build %s: %s %s' %
                   (' '.join(self.outs), self.rule, ' '.join(self.ins)))
        if len(self.deps) > 0:
            file.write(' | %s' % (' '.join(self.deps)))
        file.write('\n')
        for key, val in self.vars.items():
            if key not in defaults or defaults[key] != val:
                file.write('  %s = %s\n' % (key, val))


class Generator:
    """
    The `Generator` collects rules and build edges and finally writes a Ninja build file.

    The rules describe how specific file types are built (e.g., shared libraries), while a build
    edge describes one concrete file to build. The generator comes with a number of builtin rules
    for C, C++, and Rust, but can be extended by additional rules via `Generator.add_rule`. Build
    edges can be added with `Generator.add_build`.

    Typically, the build edges are added to the generator via the environment (`Env`). For example,
    the method `Env.cc` will add a build edge for the rule `cc` to the generator that is given to
    `Env.cc`. The reasoning is that `Env` holds the required values in terms of tools, compiler
    flags, and paths for the build of a specific file and hence will create a build edge based on
    this information and add them to the `Generator`.
    """

    def __init__(self):
        """
        Creates a new `Generator` with the default rules.
        """

        self._build_dir = os.environ.get('NPBUILD')
        self._debug = os.environ.get('NPDEBUG', '0') == '1'
        self._rules = {}
        self._build_edges = []
        self._globs = []
        self._build_files = []

        # default rules
        self.add_rule('install', Rule(
            cmd='install $instflags $in $out && touch $out',
            desc='INSTALL $out'
        ))
        self.add_rule('cpp', Rule(
            cmd='$cpp -MD -MF $out.d -P $cppflags $in -o $out',
            deps='gcc',
            depfile='$out.d',
            desc='CPP $out'
        ))
        self.add_rule('cc', Rule(
            cmd='$cc -MD -MF $out.d $ccflags -c $in -o $out',
            deps='gcc',
            depfile='$out.d',
            desc='CC $out'
        ))
        self.add_rule('cxx', Rule(
            cmd='$cxx -MD -MF $out.d $cxxflags -c $in -o $out',
            deps='gcc',
            depfile='$out.d',
            desc='CXX $out'
        ))
        self.add_rule('ar', Rule(
            cmd='$ar rc $arflags $out $in && $ranlib $out',
            desc='AR $out'
        ))
        self.add_rule('link', Rule(
            cmd='$link -o $out $in $linkflags',
            desc='LINK $out'
        ))
        self.add_rule('shlink', Rule(
            cmd='$shlink -shared -o $out $in $shlinkflags',
            desc='SHLINK $out'
        ))
        self.add_rule('strip', Rule(
            cmd='$strip -o $out $in',
            desc='STRIP $out'
        ))
        self.add_rule('cargo', Rule(
            cmd='cd $dir && $env $cargo $cargoflags',
            desc='CARGO $out',
            # recheck which output files have changed after the command to only relink the
            # executables where the library generated by Rust actually changed
            restat=True,
        ))

        # special build edge for 'always-rebuild' build edges
        self._build_edges.append(BuildEdge(
            'phony',
            outs=['always'],
            ins=[],
            deps=[]
        ))

    def add_rule(self, name: str, rule: Rule):
        """
        Adds a new rule to this generator.

        These rules can later be referenced when adding build edges via `Generator.add_build`. Note
        that Rule names are unique and cannot be added twice.

        Parameters
        ----------
        :param name: The name of the rule
        :param rule: The `Rule` object to add
        """

        assert name not in self._rules
        self._rules[name] = rule

    def add_build(self, edge: BuildEdge):
        """
        Adds a new build edge to this generator.

        This build edge assigns concrete values to the variables defined by the rule. As the
        referenced rule is now used, the generator will write both the rule and the build edge to
        the Ninja build file when `Generator.write_to_file` is called. Note that the rule this build
        edge refers to needs to exist.

        Parameters
        ----------
        :param name: The name of the rule
        :param rule: The `Rule` object to add
        """

        assert edge.rule in self._rules

        if self._debug:
            for ex_edge in self._build_edges:
                # skip edges that don't have a calltrace (e.g., the always-rebuild rule)
                if ex_edge.calltrace is None:
                    continue

                for out in ex_edge.outs:
                    assert out not in edge.outs, \
                        "Output '{}' is already produced by the build edge added here:\n{}".format(
                            out, ''.join(traceback.format_list(ex_edge.calltrace)))
            edge.calltrace = traceback.extract_stack()

        self._rules[edge.rule].refs += 1
        self._build_edges.append(edge)

    def _add_glob(self, pattern):
        """
        Adds the given pattern to the list of globs

        These globs will be written to file in `Generator.write_to_file`.
        """

        self._globs += [pattern]

    def _add_build_file(self, file):
        """
        Adds the given file to the list of encountered `build.py` files

        This list will be written to file in `Generator.write_to_file`.
        """

        self._build_files += [file]

    def write_to_file(self, defaults: dict[str, str] = None):
        """
        Writes the Ninja build file according to the so far added rules and build edges.

        The written file is stored in `$NPBUILD/build.ninja` and will be overwritten, if it already
        exists. Additionally, a `$NPBUILD/.build.deps` file will be written, which holds the
        dependencies of the regeneration rule. This regeneration rule defines when the build.ninja
        file needs to be regenerated and how. The rule therefore depends on all `build.py` files in
        the current directory or any subdirectory.

        Parameters
        ----------
        :param defaults: the default variables. If the value of a variable for a particular build
            edge is the same as the value in the default variables, the variable will not be
            specified for the build edge. As such, default variables help to reduce the size of the
            ninja build file. By default (if `defaults` is `None`), Ninjapie determines these
            defaults automatically by chosing the most used value for each default variable. You can
            however specify a custom set of default variables instead. For example, this can be used
            for debugging by specifying an empty dict so that all variables will be specified
            explicitly for every build edge, which makes it easier to read the ninja build file.
        """

        outdir = self._build_dir

        build_file = outdir + '/build.ninja'
        dep_file = outdir + '/.build.deps'
        glob_file = outdir + '/.build.globs'

        # rules and build edge to automatically regenerate the build.ninja
        self.add_rule('generator', Rule(
            cmd='python -B build.py',
            depfile=outdir + '/.build.deps',
            pool='build_pool',
            generator='1',
            desc='Regenerating build.ninja',
        ))
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.add_build(BuildEdge(
            'generator',
            outs=[build_file],
            ins=[],
            deps=glob(this_dir + "/*.py"),
        ))

        self._finalize_deps()
        if defaults is None:
            defaults = self._determine_defaults()

        # generate build.ninja
        with open(build_file, 'w', encoding='utf-8') as file:
            file.write('# This file has been generated by the ninjapie build system.\n')
            file.write('\n')

            for key, val in defaults.items():
                file.write('%s = %s\n' % (key, val))
            file.write('\n')

            for name, rule in self._rules.items():
                if rule.refs > 0:
                    rule._write_to_file(name, file)
            file.write('\n')

            # separate pool for the build.ninja regeneration to run that alone
            file.write('pool build_pool\n')
            file.write('  depth = 1\n')
            file.write('\n')

            for edge in self._build_edges:
                edge._write_to_file(defaults, file)

        # generate deps of build.ninja
        build_files = ['build.py'] + self._build_files
        with open(dep_file, 'w', encoding='utf-8') as file:
            file.write(build_file + ': ' + ' '.join(build_files))

        # generate files with all globs
        with open(glob_file, 'w', encoding='utf-8') as file:
            for glb in self._globs:
                file.write(glb + '\n')

    def write_compile_cmds(self):
        """
        Writes a `compiler_commands.json` file for `clangd`.

        This file is leveraged by the language server `clangd` to know how your source files are
        build. The file is written to `$NPBUILD/compile_commands.json` and will be overwritten, if
        existing. Note that only the rules `cxx` and `cc` are considered.
        """

        outdir = self._build_dir

        # generate compile_commands.json for clangd
        with open(outdir + '/compile_commands.json', 'w', encoding='utf-8') as cmds:
            cmds.write('[\n')
            base_dir = os.getcwd()
            count = 0
            for edge in self._build_edges:
                if edge.rule in ('cxx', 'cc'):
                    assert len(edge.ins) == 1
                    if count > 0:
                        cmds.write(',\n')
                    cmds.write('  {\n')
                    cmds.write('    "directory": "{}",\n'.format(base_dir))
                    cmds.write('    "file": "{}",\n'.format(edge.ins[0]))
                    cmds.write('    "command": "{}"\n'.format(self._get_clang_flags(edge)))
                    cmds.write('  }')
                    count += 1
            cmds.write('\n]\n')

    def _get_clang_flags(self, bedge: BuildEdge) -> str:
        """
        Determines the flags for clang or clang++ for the given build edge.

        Parameters
        ----------
        :param bedge: the build edge for which to generate the flags

        Returns
        -------
        A string with the flags
        """

        flags = 'ccflags' if bedge.rule == 'cc' else 'cxxflags'
        flag_str = 'clang' if bedge.rule == 'cc' else 'clang++'
        flag_str += ' ' + bedge.vars[flags].replace('"', '\\"')
        # remove all machine specific flags, because clang does not support all ISAs, etc.
        return re.sub(r'\s+-m\S+', '', flag_str)

    def _determine_defaults(self) -> dict[str, str]:
        """
        Determines the default values for the used variables.

        Ninja supports global variables whose values are used whenever a variable is not set for a
        particular build edge. For that reason, Ninjapie auto-generates these global variables based
        on the most used values in all build edges. This approach thus reduces the size of the
        `build.ninja` file.

        Returns
        -------
        A dictionary with the variable names and values
        """

        # first count the number of times for each value and each variable
        vars = {}
        for edge in self._build_edges:
            for key, val in edge.vars.items():
                if key not in vars:
                    vars[key] = {}
                if val in vars[key]:
                    vars[key][val] += 1
                else:
                    vars[key][val] = 1

        # now use the most-used value for each variable as the default
        defaults = {}
        for name, vals in vars.items():
            max_count = 0
            max_key = None
            for key, count in vals.items():
                if count > max_count:
                    max_key = key
                    max_count = count
            if max_key is not None:
                defaults[name] = max_key
        return defaults

    def _finalize_deps(self):
        """
        Finalizes the dependencies of all build edges.

        When build edges use libraries, we first collect them under the `libs` field. After all
        libraries that we build ourself are known, we complete the dependencies of the build edges
        based on these `libs`. That is, whenever we build the library ourself, we add the path to
        the built library to the dependency. Otherwise, we assume that the library exists in some
        system directory and will not change (we do not add it to the dependencies).
        """

        libs = self._collect_libs()
        for edge in self._build_edges:
            for lib in edge.libs:
                stname = 'lib' + lib + '.a'
                shname = 'lib' + lib + '.so'
                for path in edge.lib_path:
                    if path in libs:
                        if shname in libs[path]:
                            edge.deps.append(libs[path][shname])
                            break
                        if stname in libs[path]:
                            edge.deps.append(libs[path][stname])
                            break

    def _collect_libs(self) -> dict[str, dict[str, str]]:
        """
        Collects the libraries that we build ourself.
        """

        libs = {}
        for edge in self._build_edges:
            for out in edge.outs:
                if out.endswith('.a') or out.endswith('.so'):
                    dir = os.path.dirname(out)
                    if dir not in libs:
                        libs[dir] = {}
                    libs[dir][os.path.basename(out)] = out
        return libs
