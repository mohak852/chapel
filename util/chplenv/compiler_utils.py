""" Backend compiler utility functions for chplenv modules """
import os
import re
import sys

from collections import namedtuple

chplenv_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(chplenv_dir))

from utils import memoize, run_command


@memoize
def get_compiler_name(compiler):
    if compiler == 'aarch64-gnu':
        return 'aarch64-unknown-linux-gnu-gcc'
    elif 'gnu' in compiler:
        return 'gcc'
    elif compiler.startswith('cray-prgenv-'):
        return 'cc'
    elif compiler == 'clang':
        return 'clang'
    elif compiler == 'intel':
        return 'icc'
    elif compiler == 'pgi':
        return 'pgcc'
    return 'other'


@memoize
def get_compiler_version(compiler):
    version_string = '0'
    if 'gnu' in compiler:
        # Asssuming the 'compiler' version matches the gcc version
        # e.g., `mpicc -dumpversion == gcc -dumpversion`
        version_string = run_command([get_compiler_name(compiler), '-dumpversion'])
    elif 'cray-prgenv-cray' == compiler:
        version_string = os.environ.get('CRAY_CC_VERSION', '0')
    return CompVersion(version_string)


@memoize
def CompVersion(version_string):
    """
    Takes a version string of the form 'major', 'major.minor',
    'major.minor.revision', or 'major.minor,revision.build' and returns the
    named tuple (major, minor, revision, build). If minor, revision, or build
    are not specified, 0 will be used for their value(s)
    """
    CompVersionT = namedtuple('CompVersion', ['major', 'minor', 'revision', 'build'])
    match = re.search(u'(\d+)(\.(\d+))?(\.(\d+))?(\.(\d+))?', version_string)
    if match:
        major    = int(match.group(1))
        minor    = int(match.group(3) or 0)
        revision = int(match.group(5) or 0)
        build    = int(match.group(7) or 0)
        return CompVersionT(major=major, minor=minor, revision=revision, build=build)
    else:
        raise ValueError("Could not convert version '{0}' to "
                         "a tuple".format(version_string))


def compiler_is_prgenv(compiler_val):
  return (compiler_val.startswith('cray-prgenv') or
     os.environ.get('CHPL_ORIG_TARGET_COMPILER','').startswith('cray-prgenv'))


#
# Determine whether a given compiler's default compilation mode
# supports standard atomics by running the compiler and checking
# how it expands key feature-test macros.
#
# The assumption is that if standard atomics make it into the
# compiler's default compilation mode, then they actually work.
# If they are not available in the default mode, they probably
# have problems and we don't want to use them.
#
# Due to the command-line options required, this works for GCC,
# Clang, and the Intel compiler, but probably not others.
#
def has_std_atomics(compiler_val):
    try:
        compiler_name = get_compiler_name(compiler_val)
        if compiler_name == 'other':
            return False
        cmd = "echo __STDC_VERSION__ __STDC_NO_ATOMICS__ | "
        cmd += compiler_name + " -E -x c - | sed -e '/^\#/d'"
        out = run_command(['sh', '-c', cmd]).split()
        version = out[0].rstrip("L")
        atomics = out[1]
        if version == "__STDC_VERSION__" or int(version) < 201112:
            return False
        # If the atomics macro was expanded, then we do not have support.
        if atomics != "__STDC_NO_ATOMICS__":
            return False
        return True
    except:
        return False
