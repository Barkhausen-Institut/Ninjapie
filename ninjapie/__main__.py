import argparse
from glob import glob
import os
import subprocess
import sys


def all_files(build_dir):
    """Collects a string with all files found by the patters in the globs file"""
    files = ''
    try:
        with open(build_dir + '/.build.globs', 'r') as file:
            for line in file.readlines():
                files += '\n'.join(glob(line.strip(), recursive=True))
                files += '\n'
    except FileNotFoundError:
        pass
    return files


def clean(build_dir, args, ninja_args):
    def remove_dir(path):
        """Removes the given directory recursively"""
        for d in os.listdir(path):
            try:
                remove_dir(path + '/' + d)
            except OSError:
                os.remove(path + '/' + d)
        os.rmdir(path)

    remove_dir(build_dir)
    return 0


def build(build_dir, args, ninja_args):
    reconf = args.force_regen
    root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    all_files_path = build_dir + '/.build.files'
    build_file = build_dir + '/build.ninja'

    # export PYTHONPATH to find the ninjapie modules
    python_path = os.environ.setdefault('PYTHONPATH', '')
    os.environ['PYTHONPATH'] = root_dir + ': ' + python_path

    # check if we need to reconfigure
    if not reconf:
        try:
            # check whether files have been added or removed
            old_files = open(all_files_path, 'r').read()
            new_files = all_files(build_dir)
            # if the list of files changed, we need to reconfigure
            reconf = old_files != new_files
        except FileNotFoundError:
            reconf = True
            pass

    # run configure if not done before or it's required
    if reconf or not os.path.isfile(build_file):
        try:
            # run build.py, but don't write *.pyc files
            subprocess.check_call(['python3', '-B', 'build.py'])
        except:
            return 1

        # store new list of files from globs
        new_files = all_files(build_dir)
        with open(all_files_path, 'w') as file:
            file.write(new_files)

    # now build everything with ninja
    try:
        subprocess.check_call(['ninja', '-f', build_file] + ninja_args, stdout=sys.stderr.buffer)
    except:
        # ensure that we regenerate the build.ninja next time. Since ninja does not accept the
        # build.ninja, it will also not detect changes our build files in order to regenerate it.
        # Therefore, force a regenerate next time by removing the file.
        os.remove(all_files_path)
        return 1

    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # determine and create build dir
    build_dir = os.environ.setdefault('NPBUILD', 'build')
    if not os.path.isdir(build_dir):
        os.makedirs(build_dir)

    # define command line arguments
    parser = argparse.ArgumentParser(
        description='This is the Ninjapie build system. '
        'Besides the supported command line arguments all additional arguments, '
        'preceeded by "--", will be passed to ninja. For example "ninjapie -- -v".'
    )
    subparsers = parser.add_subparsers(
        title='commands',
        description='The command to execute (build by default)',
    )

    parser_clean = subparsers.add_parser('clean', description='Removes the build directory')
    parser_clean.set_defaults(func=clean)

    parser_build = subparsers.add_parser(
        'build', description='Builds everything (the default command)')
    parser_build.add_argument('-f', '--force-regen', action='store_true', default=False,
                              help='force a regeneration of the ninja build file')
    parser_build.set_defaults(func=build)

    # we pass everything after "--" directly to ninja
    try:
        ninja_start = argv.index('--')
        ninja_args = argv[ninja_start + 1:]
        our_args = argv[0:ninja_start]
    except:
        ninja_args = []
        our_args = argv

    # parse arguments and run command
    args = parser.parse_args(our_args)
    try:
        res = args.func(build_dir, args, ninja_args)
    except:
        args.force_regen = False
        res = build(build_dir, args, ninja_args)
    return res


if __name__ == "__main__":
    sys.exit(main())
