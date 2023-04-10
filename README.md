[![PyPI version](https://badge.fury.io/py/ninjapie.svg)](https://badge.fury.io/py/ninjapie)
![pylint](https://github.com/Barkhausen-Institut/Ninjapie/actions/workflows/pylint.yml/badge.svg)

Ninjapie
========

Ninjapie is a tool for automating the building of software. It builds upon [Ninja](https://ninja-build.org) and provides a Python API to describe the build. The basic idea is to take the flexibility and simplicity of [SCons](https://scons.org) and combine it with the performance of Ninja.

# Why Ninjapie?

Ninjapie was originally created for [M³](https://github.com/Barkhausen-Institut/M3), a custom operating system containing hundreds of thousands of lines of Code in C, C++, and Rust, running on different hardware platforms and architectures, and having several non-standard build requirements. As such, the goals for Ninjapie were performance, flexibility, and simplicity.

**1. Performance**

Building on top of Ninja and requiring a re-configuration only on build-script changes or added/removed files, Ninjapie is as fast as build systems can be. Even for projects like M³ Ninjapie adds almost no noticable delay to the build process.

**2. Flexibility**

In contrast to other Ninja frontends like [Meson](https://mesonbuild.com), Ninjapie builds upon Python and thus provides full flexibility in describing your build. This prevents repetitive descriptions, because functions, classes, wildcards, etc. can be used to keep build scripts concise. Furthermore, having a programming language available takes away the risk of declarative approaches that no one else might have thought of your use case before. What ever special requirement you have, rest assured that it can be fullfilled with Ninjapie.

**3. Simplicity**

Ninjagen is implemented as a simple yet powerful Python library of about 500 lines. For that reason, it is easy to understand and to customize.

# Installation

You can install Ninjapie via pip:

```Shell
$ pip install ninjapie
```

You can afterwards run `ninjapie` in your project directory to build it.

# How does Ninjapie work?

Since Ninjapie uses Ninja as its backend, the build process consists of two phases: configuration and building. The configuration phase is handled by Ninjapie, which reads the Ninjapie build scripts and generates a Ninja build file. The building phase is handled by Ninja, which is responsible to determine the outdated files and run the commands in the correct order according to the dependency tree to make everything up to date. Both phases are triggered by a shell script called `ninjapie`. This shell script will perform the (re)configuration, if required, and run Ninja afterwards.

## Environment and Generator

Ninjapie consists of an Environment and a Generator. The Environment stores all the tools, paths, and compiler flags and is used to define what target files should be built and how. The Environment can be changed to adjust the state according to the needs of a particular target file. Most importantly, the environment can be cloned so that different target files can be described independently. The generator collects all the build descriptions (called `BuildEdge`s) for the target files and is finally used to generate a Ninja build file.

## Build Scripts

A simple Ninjapie build script, called `build.py`, looks like the following:
```Python
from ninjapie import Generator, Env
gen = Generator()
env = Env()
env['CFLAGS'] += ['-Wall', '-Wextra']
env.c_exe(gen, out='hello', ins=['hello.c'])
gen.write_to_file()
```
The example describes how to produce a C executable named `hello` from the input file `hello.c`. It also sets some additional compiler flags and finally writes the resulting Ninja build file. Note that header-file dependencies are handled automatically by Ninja.

## Paths

Paths are handled in Ninjapie via `SourcePath` and `BuildPath`. The former is used to refer to source files, whereas the latter is used to refer to build files. Source files are specified relative to the current directory in `Env` and build files are specified relative to the build directory *and* current directory in `Env`. These path objects are typically not used in user code, because the methods in `Env` expect lists of strings. However, due to the way `SourcePath` and `BuildPath` are designed you can also add these paths to the list. For example, you can use `Env.cc` to build an object file and pass the resulting `BuildPath` (referring to the created object file) to `Env.c_exe` to create an executable out of the object file and possibly other source files:
```Python
obj = env.cc(gen, out='foo.o', ins=['foo.c'])
env.c_exe(gen, out='hello', ins=[obj, 'hello.c'])
```

## Globbing

Ninjapie also supports globbing via `Env.glob`. For example, you can build all C files in the current directory to an executable in the following way:
```Python
env.c_exe(gen, out='hello', ins=env.glob(gen, '*.c'))
```
Note however that globbing has the side effect that the required build steps might change on added or removed files. For that reason, Ninjapie records the glob patterns and regenerates the Ninja build file whenever any file is added or removed. In other words, using `Env.glob` is a trade-off between more convenience and faster builds, because Ninjapie needs to perform additional checks for globs. Therefore, using globbing extensively might cause a measurable overhead. Note that this also means that *only* this function should be used for globbing, because all other ways bypass Ninjapie and therefore lead to potentially outdated Ninja build files.

# Examples

You can find several examples in the `tests` directory. They show how Ninjapie can be used for several languages, demonstrate the features of Ninjapie, and verify its correctness.

# Limitations

- Ninjapie is currently focused on Linux. The API should be general enough so that it can be adapted for other platforms, but this has not been done yet.
- Currently there is only builtin support for Assembler, C, C++, and Rust.
- In general, the feature set is currently minimal. While this is also good news, it means that it might not have builtin support for some use case you have. However, as custom rules and build edges can be created and Ninjapie is Python-based, support for these use cases can be implemented on top (see `tests/latex` as an example).
