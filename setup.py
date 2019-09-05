from setuptools import find_packages, setup

setup(
    name='icinga2-exporter',
    version='0.1.0',
    packages=find_packages(),
    author='thenodon',
    author_email='anders@opsdis.com',
    url='https://github.com/opsdis/icinga2-exporter',
    license='GPLv3',
    include_package_data=True,
    zip_safe=False,
)
