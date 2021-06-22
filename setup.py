


#from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import setup, find_packages

#from manage_version import get_version


def read(fname):
    return open(join(dirname(__file__), fname)).read()


setup(
    name='icinga2-exporter',
    #version=get_version(),
    #version_config=True,
    version_config={
        "template": "{tag}",
        "dev_template": "{tag}.dev{ccount}",
        "dirty_template": "{sha}",
        "starting_version": "0.0.1",
        "version_callback": None,
        "version_file": None,
        "count_commits_from_version_file": False,
        "branch_formatter": None
    },
    setup_requires=['setuptools-git-versioning'],
    packages=find_packages(),
    author='thenodon',
    author_email='anders@opsdis.com',
    url='https://github.com/opsdis/icinga2-exporter',
    license='GPLv3',
    include_package_data=True,
    zip_safe=False,
    description='A Prometheus exporter for Icinga2',
    install_requires=read('requirements.txt').split(),
    #packages=find_packages(where='icinga2-exporter'),
    #package_dir={'': 'icinga2-exporter'},
    #  py_modules=[splitext(basename(path))[0] for path in glob('icinga2-exporter/*.py')],
    python_requires='>=3.6',
)
