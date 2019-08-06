from    .logging        import  handle_exception, Level
from    operator        import  getitem
from    functools       import  reduce

@handle_exception()
def join_string_array(array, delimiter=', '):
    '''
        Joins and adjusts a text array.
        Args    :
            array       : An array of strings.
            delimiter   : Delimiter.
        Returns :
            A single string
    '''
    return delimiter.join([ x.strip() for x in array if x.strip() != ''])

@handle_exception(level= Level.ERROR, log= False)
def dict_path(nested_dict, path):
    '''
        Gets the value in path from the nested dict.
        Args    :
            nested_dict : A python dict.
            path        : The path to the value as a list.
        Returns :
            The value at nested_dict[path[0]][path[1]] ...
    '''
    return reduce(getitem, path, nested_dict)

@handle_exception(level=Level.ERROR, log= False)
def safe_getitem(array_or_dict, key):
    '''
        Gets an element from a dict or an array, return None if the key is not found or out of range.
        Args    :
            array_or_dict   : The array or dict to look into.
            key             : The key to look for.
        Returns : The value if found else None.
    '''
    return array_or_dict[key]
