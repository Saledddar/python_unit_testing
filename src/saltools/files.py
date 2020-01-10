'''File manipulation.

    File manipulation.
'''

from    .logging    import Logger, handle_exception

import  stat
import  os
import  re

def rmtree          (
    folder  ):
    '''Removes folders.
        Removes the folder and any readonly files.

        Args:
            folder (str ): The folder to remove.
    '''
    for ROOT, dirs, files in os.walk(folder, topdown=False):
        for name in files:
            filename = os.path.join(ROOT, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(ROOT, name))
    os.rmdir(folder)
def c_path_folder   (
    file_   ,
    *args   ):
    '''Generates a in the same folder as file_.

        Args:
            *args  (str ): New relative path.
        
        Returns:
            str : the created path. 
    '''
    abs_path    = os.path.abspath(file_)
    folder      = os.path.dirname(abs_path)
    path        = os.path.join(folder, *args)
    directory   = os.path.dirname(path)

    if      not os.path.exists(directory):
        os.makedirs(directory)

    return path
def g_filders       (
    root                , 
    regex               , 
    absolute    = False , 
    files       = True  , 
    folders     = True  , 
    sub_dirs    = True  ):
    '''Gets all files and/or folders matching a regex.

    '''
    compiled        = re.compile(regex)
    result          = []
    for dirpath, dirnames, filenames in os.walk(root) :
        #Select files matching the expression
        if      files    :
            for file in filenames :
                if      compiled.match(file):
                    result.append(os.path.join(dirpath,file) if absolute else file )
        if folders      :
            for folder in dirnames :
                if      compiled.match(folder):
                    result.append(os.path.join(dirpath,folder) if absolute else folder )
        #Break if no sub-directories
        if not sub_dirs :
            break
    return result