'''File manipulation.

    File manipulation.
'''

from    .logging    import Logger, handle_exception

import  stat
import  os
import  re

def rmtree                          (
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
def create_path_in_script_directory (
    *args   ):
    '''Generates a path in the caller script folder.

        Generates a path in the directory of the caller script.
        If the relative path doesn't exist, it is created.
        If the path contains a file, it is not created.
        
        Args:
            *args  (str ): relative path to the directory of the caller module.
        
        Returns:
            str : the created path. 
    '''
    file_name           = os.path.join(*args)
    script_file_path    = os.path.realpath(__file__)
    script_directory    = os.path.dirname(script_file_path)

    #Make sure directory exists if nested
    directory =os.path.join(script_directory,os.path.dirname(file_name))
    if not os.path.exists(directory):
        os.makedirs(directory)

    #Build the file path using the file name and the directory path
    file_path   = os.path.join(script_directory,file_name)

    #return
    return file_path
def g_filders                       (
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