from setuptools import setup, find_packages
import sys, os

README = open('README.rst').read()

setup(
    name                            = 'saltools'                                ,
    version                         = '0.1.4'                                   ,
    description                     = 'Some usefull code'                       ,
    long_description                = README                                    ,
    long_description_content_type   = 'text/markdown'                           ,
    classifiers                     =[
          'Development Status :: 4 - Beta'                                      ,
          'Intended Audience :: Developers'                                     ,
          'License :: OSI Approved :: MIT License'                              ,
          'Operating System :: Microsoft :: Windows'                            ,
          'Programming Language :: Python'                                      ,
          'Topic :: Software Development :: Libraries'                          ],
    keywords                        = 'logging exception scheduling generics '  ,
    author                          = 'saledddar'                               ,
    author_email                    = 'saledddar@gmail.com'                     ,
    url                             = 'https://github.com/Saledddar/saltools'   ,
    license                         = 'MIT'                                     ,
    include_package_data            = True                                      ,
    zip_safe                        = False                                     ,
    packages                        = ['saltools']                              ,
    package_dir                     = {'': 'src'}                               ,
    install_requires                = [
        'lxml'              ,
        'requests'          ]
)
