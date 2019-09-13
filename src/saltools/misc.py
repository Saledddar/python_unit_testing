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
            str_iterable(Iterable: str  ): The strings to join.
            delimiter   (str            ): Character used to join. 

        Returns:
            bool    : Description of return value
    '''
    return delimiter.join([ x.strip() for x in str_iterable if x.strip() != ''])
@handle_exception(
    level   = Level.ERROR  , 
    log     = False         )
def g_dict_path(
    nested_dict , 
    path        ):
    '''Gets a value from a nested dict.
        
        Gets the value specified by path from the nested dict.
        
        Args:
            nested_dict (dict                   ): A python dict.
            path        (Iterable: str  | str   ): An iterable of keys or a path string as `a.b.c`.

        Returns:
            Object : The value at nested_dict[path[0]][path[1]] ...
    '''
    path    = path if isinstance(path, list) else path.split('.')
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
@handle_exception()
def print_progress(
    current             , 
    total               , 
    message             ,
    p_percentile= True  ,
    p_current   = True  ,
    add_one     = True  ):
    '''Prints loop progess.

        Prints loop progress with a message.

        Args:
            current     (int    ): The current index being processed.
            total       (int    ): Total number of items to process.
            message     (str    ): Message to print on console.
            p_percentile(bool   ): If True, prints the progress as a percentile.
            p_current   (bool   ): If True, prints the progress as current/total.
            add_one     (bool   ): If True, adds one to the current progress, useful for zero based indexes.
    '''
    if add_one :
        current +=1

    current_format  = '{{:>{total:}}}/{{:<{total:}}}'.format(total=len(str(total)))
    percentile_str  = '{:4.2f}% '.format(100*current/total) if p_percentile else ''
    current_str     = current_format.format(current, total) if p_current else ''
    progress_str    = '{}: {}{}!'.format(message, percentile_str, current_str)

    print(progress_str, end='\r')
    
    if current == total :
        print('\n')
        