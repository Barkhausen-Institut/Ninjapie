import os


class SourcePath(str):
    """
    A path for source files

    This class is used to refer to source files. These are specified relative to the current
    directory in the given environment (`Env.cur_dir`).

    `SourcePath` implements `__str__` and `__repr__` and can thus be used as a string (the contained
    path).
    """

    def __init__(self, path: str):
        """
        Creates a new `SourcePath` that simply uses the given path

        Parameters
        ----------
        :param path: the path
        """

        self._path = path

    @staticmethod
    def new(env, path):
        """
        Creates a new `SourcePath` from given path object

        The path object can be a `SourcePath`, `BuildPath` or `str`. The former two just create a
        `SourcePath` with the path within the existing object, whereas `str` is interpreted relative
        to `Env.cur_dir`.

        Parameters
        ----------
        :param env: the Environment
        :param path: the path object

        Returns
        -------
        A `SourcePath` object
        """

        if isinstance(path, SourcePath):
            return SourcePath(path._path)
        if isinstance(path, BuildPath):
            return SourcePath(path._path)
        return SourcePath(env.cur_dir + '/' + path)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return repr(self._path)


class BuildPath(str):
    """
    A path for build files

    This class is used to refer to build files. These are specified relative to the current
    directory and the build directory in the given environment (`Env.cur_dir`). So, basically build
    files are put into `"$NPBUILD/" + Env.cur_dir`.

    `BuildPath` implements `__str__` and `__repr__` and can thus be used as a string (the contained
    path).
    """

    def __init__(self, path: str):
        """
        Creates a new `BuildPath` that simply uses the given path

        Parameters
        ----------
        :param path: the path
        """

        self._path = path

    @staticmethod
    def new(env, path):
        """
        Creates a new `BuildPath` from given path object

        The path object can be a `SourcePath`, `BuildPath` or `str`. If it's build path, it simply
        creates a copy. If it's a source path, it produces a `BuildPath` consisting of
        `Env.build_dir` and the path. If it's a string, it produces a `BuildPath` consisting of
        `Env.build_dir`, `Env.cur_dir` and the string.

        Parameters
        ----------
        :param env: the Environment
        :param path: the path object

        Returns
        -------
        A `BuildPath` object
        """

        if isinstance(path, BuildPath):
            return BuildPath(path._path)
        if isinstance(path, SourcePath):
            return BuildPath(env.build_dir + '/' + path._path)
        return BuildPath(env.build_dir + '/' + env.cur_dir + '/' + path)

    @staticmethod
    def with_file_ext(env, path, ext: str):
        """
        Creates a new `BuildPath` from given path object and file extension

        This method is the same as `BuildPath.new`, but replaces the file extension of the given
        path with `ext`.

        Parameters
        ----------
        :param env: the Environment
        :param path: the path object
        :param ext: the new file extension

        Returns
        -------
        A `BuildPath` object
        """

        (root, _cur_ext) = os.path.splitext(path)
        if isinstance(path, BuildPath):
            return BuildPath(root + '.' + ext)
        if isinstance(path, SourcePath):
            return BuildPath.new(env, SourcePath(root + '.' + ext))
        return BuildPath.new(env, root + '.' + ext)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return repr(self._path)
