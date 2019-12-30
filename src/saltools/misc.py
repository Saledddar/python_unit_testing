'''Miscellaneous tools and functions.

    Module contains any function or feature that do not fall under a specific description.
'''
from    .common                     import  EasyObj
from    collections.abc             import  Iterable
from    collections                 import  OrderedDict     , defaultdict
from    sqlalchemy                  import  create_engine
from    sqlalchemy_utils.functions  import  create_database , database_exists
from    enum                        import  Enum

import  importlib
import  json
import  os

class ConfigType        (
    Enum    ):
    JSON    = 0
class DataBaseEngine    (
    Enum    ):
    SQLITE      = 0
    MSSQL       = 1
    MYSQL       = 2
    POSTGRESQL  = 3
    ORACLE      = 4

class SQLAlchemyEBuilder(
    EasyObj ):
    EasyObj_PARAMS  = OrderedDict((
        ('db_engine'    , {
            'default'   : DataBaseEngine.SQLITE ,
            'type'      : DataBaseEngine        },),
        ('user'         , {
            'default'   : 'root',
            'type'      : str   },),
        ('pwd'          , {
            'default'   : ''    ,
            'type'      : str   },),
        ('host'         , {
            'default'   : 'localhost'   ,
            'type'      : str           },),
        ('port'         , {
            'default'   : '3306'    ,
            'type'      : str       },),
        ('db'           , {
            'default'   : '/sqlite.db'  ,
            'type'      : str           },),
        ('charset'      , {
            'default'   : 'utf8mb4'     ,
            'type'      : str           },),
        ('is_create'    , {
            'default'   : True          ,
            'type'      : bool          },),))
    
    def _on_init(
        self    ):
        if      self.db_engine  == DataBaseEngine.SQLITE    :
            connection_str  = '{db_engine}://{db}'.format   (
                db_engine   = self.db_engine.name.lower()   ,
                db          = self.db                       )
        else                                                :
            connection_str  = '{db_engine}://{user}:{pwd}@{host}:{port}/{db}?charset={charset}'.format(
                db_engine   = self.db_engine.name.lower()   ,
                user        = self.user                     ,
                pwd         = self.pwd                      ,
                host        = self.host                     ,
                port        = self.port                     ,
                db          = self.db                       ,
                charset     = self.charset                  )
        if      not database_exists(connection_str)     and \
                self.is_create                              :
                create_database(
                    connection_str              ,
                    encoding        ='utf8mb4'  )
        self.engine = create_engine(connection_str)

def load_module         (
    path            ,
    name    = None  ):
    if      name == None    :
        name    = os.path.split(path)[-1][:-3]
    spec    = importlib.util.spec_from_file_location(name, path)
    module  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, name
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
    def clean_str   (
        str_        ,
        delimiter   ):
        if      str_ in [None]  :
            return ''
        str_        = str(str_)
        delimiter   = delimiter.strip()
        str_        = str_.strip()
        if      str_[:len(delimiter)]   == delimiter    :
            str_    = str_[len(delimiter):]
        if      str_[-len(delimiter):]  == delimiter    :
            str_    = str_[:-len(delimiter)]
        return str_.strip()
    strs    = []
    for str_ in str_iterable :
        clean   = clean_str(str_, delimiter)
        if      clean != '' :
            strs.append(clean)
    return delimiter.join(strs)
def g_item              (
        obj , 
        attr):
        try                                     :
            attr    = int(attr)
        except                                  :
            pass
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
    is_return_last  = True  ):
    '''Gets a value from a nested dict.
        
        Gets the value specified by path from the nested dict, return `None` on expections.
        
        Args:
            obj     (dict                   ): A python dict.
            path    (Iterable: str  | str   ): An iterable of keys or a path string as `a.b.c`.

        Returns:
            Object : The value at nested_dict[path[0]][path[1]] ...
    '''
    if      isinstance(path, str)           :
        path    = path.split(path_sep)
    if      not isinstance(path, Iterable)  :
        path    = [path]
      
    for attr in path   :
        try :
            obj   = g_item(obj, attr)
        except  :
            return default_value if default_value != None else obj if is_return_last else None
    return obj
def g_config            (
    path            = 'config.json' ,
    config_type     = None          ,
    default_config  = {}            ):
    if      not config_type                 :
        extension   = os.path.splitext(path)[-1].replace('.', '')
        config_type = g_path(
            ConfigType          , 
            extension.upper()   ,
            ConfigType.JSON     )
    if      not os.path.exists(path)        :
        return default_config
    if      config_type == ConfigType.JSON  :
        with open(path) as f :
            config = json.load(f)
    
    return config
def RecDefaultDict      (
    ): 
    '''A nice way to assign keys, values to a dict automatically.

        Credit goes to https://stackoverflow.com/questions/13151276/automatically-add-key-to-python-dict. 
    '''
    return defaultdict(RecDefaultDict)