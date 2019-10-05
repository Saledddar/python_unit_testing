from    setuptools  import  setup   , find_packages
from    os.path     import  join    , dirname         , abspath
import  sys

BASE_DIR    = abspath(dirname(__file__))
README      = open(join(BASE_DIR, 'README.rst')).read()
REQS        = [line.strip() for line in open(join(BASE_DIR, 'requirements.txt')).readlines() if line.strip()]
#Check for BOM
#if    '' in REQS[0] :
#      REQS[0] = 
print(REQS)
setup(
    name                            = 'saltools'                                ,
    version                         = '0.1.7'                                   ,
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
    install_requires                = REQS                                      )
