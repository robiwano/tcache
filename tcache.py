#!/usr/bin/env python
"""A simple python script template.
"""

from __future__ import print_function
import os, shutil, subprocess, platform
import sys
import argparse
import hashlib
import time

TCACHE_DIRECTORY = os.getenv('TCACHE_DIRECTORY')
TCACHE_EXPIRATION_DAYS = os.getenv('TCACHE_EXPIRATION_DAYS')
TCACHE_SKIP_ARGS = os.getenv('TCACHE_SKIP_ARGS')
TCACHE_BASEDIR = os.getenv('TCACHE_BASEDIR')
if TCACHE_BASEDIR == None:
    TCACHE_BASEDIR = os.getenv('CCACHE_BASEDIR')


# Read file as bytes
def get_bytes_from_file(filename):
    return open(filename, "rb").read()


# Run the process, and store results to cache
def run_process(arguments, path, key_exe):
    if not os.path.exists(path):
        os.mkdir(path)
    out = open(os.path.join(path, key_exe + '.output'), "wb")
    p = subprocess.Popen(arguments,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    for line in p.stdout:
        sys.stdout.buffer.write(line)
        out.write(line)
    retcode = p.wait()
    with open(os.path.join(path, key_exe + '.retval'), "w") as file:
        file.write(str(retcode))
    return retcode


# Get file creation date
def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


# Check if there is a cached result available
def cache_folder_has_key(path, key_exe):
    retval_path = os.path.join(path, key_exe + '.retval')
    if not os.path.exists(retval_path):
        return False
    if TCACHE_EXPIRATION_DAYS != None:
        exp_time = creation_date(
            retval_path) + int(TCACHE_EXPIRATION_DAYS) * 86400
        if time.time() >= exp_time:
            return False
    return True


# Remove all files in the given folder
def clear_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


# Output the cached result
def output_cache(path, key_exe):
    with open(os.path.join(path, key_exe + '.output'), "rb") as file:
        sys.stdout.buffer.write(file.read())
    retval = 0
    with open(os.path.join(path, key_exe + '.retval'), "r") as file:
        retval = int(file.read())
    return retval


def main(arguments):
    if len(arguments) == 0:
        print("No arguments provided")
        return 1

    arg_hash = hashlib.sha256()
    exe_hash = hashlib.sha256()
    skip_args = 0
    if TCACHE_SKIP_ARGS != None:
        skip_args = int(TCACHE_SKIP_ARGS)
    for arg in arguments[skip_args:]:
        if os.path.isfile(arg):
            exe_hash.update(get_bytes_from_file(arg))
            if TCACHE_BASEDIR != None:
                arg = os.path.relpath(arg, TCACHE_BASEDIR)
        arg_hash.update(bytes(arg, 'utf-8'))

    key_arg = arg_hash.hexdigest()
    key_exe = exe_hash.hexdigest()
    path = os.path.join(TCACHE_DIRECTORY, key_arg)
    do_execute = True
    if os.path.isdir(path):
        if cache_folder_has_key(path, key_exe):
            do_execute = False
        else:
            clear_folder(path)
    if do_execute:
        return run_process(arguments, path, key_exe)
    else:
        return output_cache(path, key_exe)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))