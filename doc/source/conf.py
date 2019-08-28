import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))

project = 'saltools'
copyright = '2019, saledddar'
author = 'saledddar'

version = '0.1.0'
release = '0.1.0'

todo_include_todos = False

extensions = [
    'sphinx.ext.autodoc'        ,
    'sphinx.ext.imgmath'        ,
    'sphinx.ext.viewcode'       ,
    'sphinx.ext.napoleon'       ,
    'sphinx.ext.intersphinx'    ]
apidoc_module_dir = '../../saltools'
apidoc_output_dir = '.'
apidoc_excluded_paths = ['tests']
apidoc_separate_modules = True
autosummary_generate    = True
source_suffix = '.rst'
master_doc = 'index'

intersphinx_mapping = {
    'python'    : ('https://docs.python.org/3', None),
    'requests'  : ('https://2.python-requests.org/en/master/', None)
    }


templates_path = ['_templates']

exclude_patterns = []


html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']
