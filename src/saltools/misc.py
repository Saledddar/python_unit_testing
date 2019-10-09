'''Miscellaneous tools and functions.

    Module contains any function or feature that do not fall under a specific description.
'''
from    .common         import  EasyObj
from    collections.abc import  Iterable
from    collections     import  OrderedDict
from    sqlalchemy      import  create_engine
from    enum            import  Enum

import  json
import  os

class ConfigType        (Enum):
    JSON    = 0
class DataBaseEngine    (Enum):
    SQLITE      = 0
    MSSQL       = 1
    MYSQL       = 2
    POSTGRESQL  = 3
    ORACLE      = 4

class SQLAlchemyEBuilder(EasyObj):
    EasyObj_PARAMS  = OrderedDict((
        ('db_engine', {
            'default'   : DataBaseEngine.SQLITE ,
            'type'      : DataBaseEngine        },),
        ('user'     , {
            'default'   : 'root',
            'type'      : str   },),
        ('pwd'      , {
            'default'   : ''    ,
            'type'      : str   },),
        ('host'     , {
            'default'   : 'localhost'   ,
            'type'      : str           },),
        ('port'     , {
            'default'   : '3306'    ,
            'type'      : str       },),
        ('db'       , {
            'default'   : '//sqlite.db' ,
            'type'      : str           },),))
    
    def _on_init(
        self    ):
        if      self.db_engine  == DataBaseEngine.SQLITE    :
            connection_str  = '{db_engine}://{db}'.format(
                db_engine   = self.db_engine.name.lower()   ,
                db          = self.db                       )
        else                                                :
            connection_str  = '{db_engine}://{user}:{pwd}@{host}:{port}/{db}'.format(
                db_engine   = self.db_engine.name.lower()   ,
                user        = self.user                     ,
                pwd         = self.pwd                      ,
                host        = self.host                     ,
                port        = self.port                     ,
                db          = self.db                       )
        self.engine = create_engine(connection_str)

def print_progress      (
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
def join_string_array   (
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
def g_item              (
        obj , 
        attr):
        if      isinstance(attr, str)           \
                and hasattr(obj, attr)          :
            return getattr(obj, attr)
        elif    hasattr(obj, '__getitem__')     :
            return obj[attr]
        else                                    :
            return None
def g_path              (
    obj                     , 
    path            = 0     ,
    default_value   = None  ,
    path_sep        = '.'   ,
    return_last     = True  ):
    '''Gets a value from a nested dict.
        
        Gets the value specified by path from the nested dict, return `None` on expections.
        
        Args:
            obj     (dict                   ): A python dict.
            path    (Iterable: str  | str   ): An iterable of keys or a path string as `a.b.c`.

        Returns:
            Object : The value at nested_dict[path[0]][path[1]] ...
    '''
    if      isinstance(path, str)   :
        path    = path.split(path_sep)
    if      not isinstance(path, Iterable)  :
        path    = [path]
      
    for attr in path   :
        try :
            obj   = g_item(obj, attr)
        except  :
            return default_value if default_value != None else obj if return_last else None
    return obj
def g_config            (
    path        = 'config.json' ,
    config_type = None          ):
    if      not config_type                 :
        extension   = os.path.splitext(path)[-1].replace('.', '')
        config_type = g_path(
            ConfigType          , 
            extension.upper()   ,
            ConfigType.JSON     )
    if      not os.path.exists(path)        :
        return {}
    if      config_type == ConfigType.JSON  :
        with open(path) as f :
            config = json.load(f)
    
    return config
        