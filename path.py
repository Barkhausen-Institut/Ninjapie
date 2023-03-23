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
            return SourcePath(env.cur_dir + '/' + path)

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
            return BuildPath(env.build_dir + '/' + path.path)
        else:
            return BuildPath(env.build_dir + '/' + env.cur_dir + '/' + path)

    def with_file_ext(env, path: str, ext: str):
        (root, cur_ext) = os.path.splitext(path)
        if isinstance(path, BuildPath):
            return BuildPath(root + '.' + ext)
        elif isinstance(path, SourcePath):
            return BuildPath.new(env, SourcePath(root + '.' + ext))
        else:
            return BuildPath.new(env, root + '.' + ext)

    def __str__(self) -> str:
        return self.path

    def __repr__(self) -> str:
        return repr(self.path)
