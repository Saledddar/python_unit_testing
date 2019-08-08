'''Miscellaneous tools and functions.

    Module contains any function or feature that do not fall under a specific description.
'''

from    .logging        import  handle_exception, Level
from    operator        import  getitem
from    functools       import  reduce

@handle_exception()
def join_string_array(
    str_iterable        , 
    delimiter= ', '     ):
    '''Joins an iterable of strings.

        Joins an iterable of strings omiting empty strings.

        Args:
            str_iterable(Iterable: str  ): Description of arg1
            delimiter   (str            ): Description of arg2

        Returns:
            bool    : Description of return value

    '''
    return delimiter.join([ x.strip() for x in str_iterable if x.strip() != ''])

@handle_exception(
    level   = Level.ERROR  , 
    log     = False         )
def dict_path(
    nested_dict , 
    path        ):
    '''Gets a value from a nested dict.
        
        Gets the value specified by path from the nested dict.
        
        Args:
            nested_dict (dict)           : A python dict.
            path        (Iterable: str  ): An iterable if keys.
            
        Returns:
            Object : The value at nested_dict[path[0]][path[1]] ...

    '''
    return reduce(getitem, path, nested_dict)

@handle_exception(
    level   = Level.ERROR   , 
    log     = False         )
def g_safe(
    array_or_dict   , 
    key             ):
    '''Checks if key is in Iterable.

        Gets an element from a dict or an array, return None if the key is not found or out of range.
        
        Args:
            array_or_dict   : The array or dict to look into.
            key             : The key to look for.
        Returns : The value if found else None.
    '''
    return array_or_dict[key]
