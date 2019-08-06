from    .logging    import Logger, handle_exception

import  stat
import  os

@handle_exception()
def rmtree(folder):
    '''
        Removes the folder and any readonly files.
        Args    :
            folder  : The folder to remove.
    '''
    for ROOT, dirs, files in os.walk(folder, topdown=False):
        for name in files:
            filename = os.path.join(ROOT, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(ROOT, name))
    os.rmdir(folder)

@handle_exception()
def create_path_in_script_directory(*args):
    '''
        Generates a path in the directory of the script.
        If the relative path doesn't exist, it is created.
        If the path contains a file, it is not created.
        Args    :
            *args       : relative path to the directory of the caller module.
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

