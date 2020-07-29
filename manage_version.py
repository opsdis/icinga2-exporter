# -*- coding: utf-8 -*-


import os
import re
import argparse

TAG = ''
COMMIT = ''
if 'BITBUCKET_TAG' in os.environ:
    TAG = os.environ['BITBUCKET_TAG']
if 'BITBUCKET_COMMIT' in os.environ:
    COMMIT = os.environ['BITBUCKET_COMMIT']
if 'TRAVIS_TAG' in os.environ:
    TAG = os.environ['TRAVIS_TAG']
if 'TRAVIS_COMMIT' in os.environ:
    COMMIT = os.environ['TRAVIS_COMMIT']


def read_release_version():
    try:
        with open("RELEASE-VERSION", "r") as f:
            version = f.readline()
            commit = f.readline()
            return version.strip(), commit.strip()

    except FileNotFoundError as err:
        create_version()
        return read_release_version()


def write_release_version(version, commit):

    with open("RELEASE-VERSION", "w") as f:
        f.write("%s\n" % version)
        f.write("%s\n" % commit)


def get_version():
    version, commit = read_release_version()
    if version and commit:
        return version


def create_version():
    version = 'dirty_dev'
    commit = 'NA'

    # Mange version if running in bitbucket
    if TAG:
        # Create version based on bitbucket tags with the format xyz-<semantic version>
        version_part = TAG.split('-')[1]
        if re.match('([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$', version_part):
            version = version_part
            commit = COMMIT
        else:
            raise Exception(f"Not a valid version according to semantic version - {version_part}")
    write_release_version(version, commit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='manage_version')

    parser.add_argument('-m', '--mode',
                        dest="mode", help="mode is get or create", default='get')

    args = parser.parse_args()

    if args.mode == 'get':
        print(get_version())
    elif args.mode == 'create':
        create_version()
    else:
        print('Not a valid mode')





