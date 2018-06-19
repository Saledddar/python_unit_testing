from setuptools import setup, find_packages
import sys, os

README = open('README.md').read()

setup(name='saltools',
    version='0.1',
    description='',
    long_description=README,
    classifiers=[],
    keywords='',
    author='',
    author_email='',
    url='https://github.com/Saledddar/saltools',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=[]
)
