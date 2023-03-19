import os

class SourcePath(str):
    def __init__(self, path: str):
        self.path = path

    def new(env, path: str):
        if isinstance(path, SourcePath):
            return SourcePath(path.path)
        elif isinstance(path, BuildPath):
            return SourcePath(path.path)
        else:
            return SourcePath(env.cwd.path + '/' + path)

    def __str__(self) -> str:
        return self.path
    def __repr__(self) -> str:
        return repr(self.path)

class BuildPath(str):
    def __init__(self, path: str):
        self.path = path

    def new(env, path: str):
        if isinstance(path, BuildPath):
            return BuildPath(path.path)
        elif isinstance(path, SourcePath):
            return BuildPath(env['BUILDDIR'] + '/' + path.path)
        else:
            return BuildPath(env['BUILDDIR'] + '/' + env.cwd.path + '/' + path)

    def with_ending(env, path: str, ending: str):
        (root, ext) = os.path.splitext(path)
        if isinstance(path, BuildPath):
            return BuildPath(root + ending)
        elif isinstance(path, SourcePath):
            return BuildPath.new(env, SourcePath(root + ending))
        else:
            return BuildPath.new(env, root + ending)

    def __str__(self) -> str:
        return self.path
    def __repr__(self) -> str:
        return repr(self.path)
