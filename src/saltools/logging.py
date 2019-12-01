'''Logging and exception handling.

    Logging utility and exception handling.
    
    Notes:
        * This module offers multiple logging options (console, files, csv, sql database).
        * All the loggers do share the same interface and can be used interchangeably.
        * A simple wrapper for exception handling with many features.
        * After calling ``logger.start``, a thread is created for logging, ``logger.stop()`` 
          must be called after the logger is no longer needed, the logging module takes 
          care of stoping all runing loggers on ``sys.exit``.
        * Since the logging is done on a separate thread, this works well with multi-threaded 
          applications, only a single thread is responsible for writing the logs.

    Examples:
        Simple Logger usage:
        
        >>> import   saltools.logging as lg
        >>> console_logger= lg.ConsoleLogger()
        >>> console_logger.start()
            [2019-08-08T02:37:25.635229][sal-logger          ] [INFO    ]:
            Logger started      :
                Logger started!
            ====================================================================================================================
        >>> console_logger.debug({'tagA': 'messageA', 'tagB': 'messageB'})
            [2019-08-08T02:42:01.145719][sal-logger          ] [DEBUG   ]:
                tagA                :
                    messageA
                tagB                :
                    messageB
            ====================================================================================================================
        >>> #this is the same as :
        >>> console_logger.log(lg.Level.DEBUG, {'tagA': 'messageA', 'tagB': 'messageB'})
            [2019-08-08T02:43:16.385413][sal-logger          ] [DEBUG   ]:
                tagA                :
                    messageA
                tagB                :
                    messageB
            ====================================================================================================================
        >>> console_logger.stop()
            [2019-08-08T02:44:10.599576][sal-logger          ] [INFO    ]:
                Logger stop signal  :
                    Logger stoping signal received!
            ====================================================================================================================
            [2019-08-08T02:44:10.600592][sal-logger          ] [INFO    ]:
                Logger stopped      :
                    Logger stopped!
            ====================================================================================================================

        Context management example using loggers:
        
        >>> with lg.ConsoleLogger() as l :
        >>>     l.info({'tag': 'Nothing to see here!'})
            [2019-08-08T02:58:08.679558][sal-logger          ] [INFO    ]:
                    Logger started      :
                            Logger started!
            ====================================================================================================================
            [2019-08-08T02:58:09.180271][sal-logger          ] [INFO    ]:
                    tag                 :
                            Nothing to see here!
            ====================================================================================================================
            [2019-08-08T02:58:09.180271][sal-logger          ] [INFO    ]:
                    Logger stop signal  :
                            Logger stoping signal received!
            ====================================================================================================================
            [2019-08-08T02:58:09.181268][sal-logger          ] [INFO    ]:
                    Logger stopped      :
                            Logger stopped!
            ====================================================================================================================

        Exception handling example:

        >>> #Start the logger first!
        >>> console_logger.start()
        >>> @lg.handle_exception(level= lg.Level.ERROR, logger= console_logger)
        >>> def divide(a, b):
        >>>     return a/b
        >>> #If the level is not critical, the exception is logged and discarded. 
        >>> divide(1, 0)
            [2019-08-08T03:48:02.292395][sal-logger          ] [ERROR   ]:
                id                  :
                        2019-08-08T03:48:02.292395___main__.divide
                File                :
                        <ipython-input-36-ba2ef72df083>
                Origin              :
                        __main__.divide
                Type                :
                        ZeroDivisionError
                Line                :
                        3
                Code                :
                        return a/b
                Msg                 :
                        division by zero
                arg_0               :
                        1
                arg_1               :
                        1
            ====================================================================================================================
        >>> @lg.handle_exception(level= lg.Level.CRITICAL, logger= console_logger)
        >>> def divide(a, b):
        >>>     return a/b
        >>> #If the level is critical, the exception is logged and also rasied. 
        >>> divide(1, 0)
            [2019-08-08T03:56:27.750648][sal-logger          ] [CRITICAL]:
                    id                  :
                            2019-08-08T03:56:27.750648___main__.divide
                    File                :
                            <ipython-input-41-8abfa8f7aa64>
                    Origin              :
                            __main__.divide
                    Type                :
                            ZeroDivisionError
                    Line                :
                            3
                    Code                :
                            return a/b
                    Msg                 :
                            division by zero
                    arg_0               :
                            1
                    arg_1               :
                            0
            ====================================================================================================================
            ---------------------------------------------------------------------------
            ZeroDivisionError                         Traceback (most recent call last)
            ....................
            ...............
            ..........
            .....
'''
from    sqlalchemy.ext.declarative  import  declarative_base
from    sqlalchemy                  import  Column          , Integer   , String    , Text
from    sqlalchemy.exc              import  OperationalError
from    sqlalchemy.orm              import  sessionmaker
from    functools                   import  wraps   , reduce
from    collections                 import  OrderedDict
from    collections.abc             import  Callable
from    datetime                    import  datetime
from    threading                   import  Thread
from    enum                        import  Enum

from    .common                     import  EasyObj             , DummyObj
from    .misc                       import  SQLAlchemyEBuilder  , g_path

import  traceback
import  textwrap
import  inspect
import  atexit
import  queue
import  sys
import  csv
import  os

############################################################
#################### Logging
############################################################

class Level(Enum):
    '''Logging levels
    '''
    DEBUG       = 1
    INFO        = 2
    WARN        = 3
    ERROR       = 4
    CRITICAL    = 5

class Logger        (EasyObj        ):
    '''Logger base.
        
        All derived must override execute_log.
        
        Args:
            id_         (str)   : The id of the logger, must be unique when running multiple loggers.
            is_print_log(bool)  : Prints the log on the console if True.
    '''
    
    LIVE_LOGGERS    = []
    EasyObj_PARAMS          = OrderedDict((
        ('id_' , {
            'default': 'sal-logger' },),))
    
    @classmethod            
    def _EasyObj_parser     (
        cls     ,
        *args   ,
        **kwargs):
        if      len(args)               \
                or 'type' not in kwargs :
            rv  = args, kwargs
        else                            :
            type_   = globals().get(kwargs['type'])
            del kwargs['type']
            rv      = type_(*args, **kwargs)
        
        return rv
    
    @staticmethod
    @atexit.register
    def stop_all    (
        ):
        '''Stop all live loggers.

            Stops all loggers regestered at LIVE_LOGGERS
        '''
        for logger in Logger.LIVE_LOGGERS.copy():
            logger.stop()
    
    def __enter__   (
        self    ):
        self.start()
        return self
    def __exit__    (
        self        , 
        type        , 
        value       , 
        traceback   ):
        self.stop()

    def _on_init    (
        self    ):
        self._queue     = queue.Queue()
        self.is_alive   = False

        for level in Level :
            setattr(
                self                            , 
                level.name.lower()              , 
                lambda                      \
                    x                       ,\
                    l           = level     ,
                    is_one_line = None      ,
                    is_raw      = False     :\
                    self.log(
                        l           , 
                        x           , 
                        is_one_line ,
                        is_raw      ) )   
    def _loop       (
        self    ):
        '''Logging loop.

            Keeps looping!
        '''
        while True:
            item = self._queue.get()
            if      item == None:
                break
            else                :
                self._execute_log(*item)
          
        self.info('Logger stopped!')
    def _execute_log(
            self            , 
            level           , 
            log_dict        ,
            log_datetime    ,
            is_one_line     ,
            is_raw          ):
        '''Write the logs.

            Defines the logging logic set by the derived logger class.
            This is only called by the logging thread and should not be called in code.
            Must be overridden by all derived classes.
            
            Args:
                level       (Level              ): Logging level.
                log_dict    (dict               ): Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime.datetime  ): The date of the log in iso format.
            Returns: 
                str         : The log string or None.
        '''
        raise NotImplementedError()
    
    def log         (
        self                    ,         
        level                   , 
        log_dict                ,
        is_one_line    = None   ,
        is_raw         = False  ):
        '''Log the logs.

            Pushes the log to the logging queue.
            
            Args    :
                level   (Level) : The logging level.
                log_dict(dict)  : The logging dict.
        '''

        self._queue.put([
                level                           ,
                log_dict                        ,
                datetime.now().isoformat()      ,
                is_one_line                     ,
                is_raw                          ])
    def start       (
        self    ):
        '''Start loging.
        
            Starts the logging thread (self._loop)
        '''
        if      self.is_alive:
            return 
        
        self.is_alive   = True
        self._thread    = Thread(
            name    = self.id_      , 
            target  = self._loop    , 
            daemon  = True          ) 
        self._thread.start()

        self.info('Logger started!')
        
        if      self not in Logger.LIVE_LOGGERS :
            Logger.LIVE_LOGGERS.append(self)
    def stop        (
        self    ):
        '''Stop!

            No more trees are cut, Saving the planet!.
        '''
        if not self.is_alive:
            return 

        self.info('Logger stopping!')
        
        #Wait for the logger to log the remaining logs
        self._queue.put(None)
        self._thread.join()
        self.is_alive  = False 

        if self in Logger.LIVE_LOGGERS:
            Logger.LIVE_LOGGERS.remove(self)
    
class ConsoleLogger (Logger         ):
    '''Console logger.
        A simple console logger, prints the logs on console.
    '''
    EasyObj_PARAMS  = OrderedDict((
        ('is_print_log' , {'default': True }),
        ('is_one_line'     , {'default': True })))
    def _execute_log(
            self            , 
            level           , 
            log_dict        ,
            log_datetime    ,
            is_one_line     ,
            is_raw          ):

        is_one_line = is_one_line if is_one_line != None else self.is_one_line
        prefix      = '' if is_raw else f'[{log_datetime}][{self.id_:<20}] [{level.name:<8}]: '
        if      is_one_line    :
            dict_text   = '|'.join([f'{k}, {v}' for k, v in log_dict.items()])  if\
                            isinstance(log_dict, dict)                          else\
                            str(log_dict) 
            text        = f'{prefix}{dict_text}'
        else                :
            if      not isinstance(log_dict, dict)    :
                log_dict = {log_dict: ''}
            prefix          +='' if self.is_raw else '\n'
            format_message  = lambda message: '\n'+ '\n'.join(textwrap.wrap(
                        message                         , 
                        subsequent_indent   = '\t\t'    , 
                        initial_indent      = '\t\t'    , 
                        width               = 100       , 
                        break_on_hyphens    = True      )) 
            dict_text       = '\n'.join([f'\t{k:<20}:{format_message(str(v))}' for k,v in log_dict.items()])
            text            = f'{prefix}{dict_text}'+'\n'+'='*120

        if self.is_print_log    :
            print(text)

        return text
class FileLogger    (ConsoleLogger  ):
    '''Text file logger.

        Simple text file logger based on ``ConsoleLogger``, dumps the logs generated by ``ConsoleLogger`` to txt files.

        Args:
            root        (str    ): The root directory to save the logs, logs will be saved under 
                                  root/id_.
            is_overwrite   (bool   ): If True, always erase previous logs on instance creation.
            is_combine     (bool   ): If True, all levels are is_combined in one file ``is_combined.log``.
    '''

    EasyObj_PARAMS  = OrderedDict((
        ('is_overwrite' , {'default': False}),
        ('is_combine'   , {'default': True }),
        ('root'         , {'default': '.'}  )))
    
    def _on_init    (
        self    ):
        logs_path   = os.path.join(self.root, self.id_)
        #Check and create the root directory
        if not os.path.isdir(logs_path):
            os.makedirs(logs_path)

        #Check all log levels files:
        if not self.is_combine and self.is_overwrite:
            for level in Level :
                path    = os.path.join(logs_path, level.name+ '.log')
                open(path, 'w').close()

        elif self.is_combine and self.is_overwrite:
            path    = os.path.join(logs_path, 'is_combined'+ '.log')
            open(path, 'w').close()
    def _g_path     (
        self    , 
        level   ):
        '''Correct logging path for ``level``.

            Get the correct file path to save the log
            
            Args:
                level   (Level) : The log level.
            
            Returns:
                str     : Logging file path. 
        '''
        return os.path.join(
            self.root                                           , 
            self.id_                                      , 
            ('is_combined' if self.is_combine else level.name)+ '.log')
    def _execute_log(
            self            , 
            level           , 
            log_dict        ,
            log_datetime    ,
            is_one_line     ,
            is_raw          ):
        text    = super()._execute_log(
            level       , 
            log_dict    ,
            log_datetime,
            is_one_line ,
            is_raw      )

        with open(self._g_path(level),'a') as f :
            f.write(text+'\n')
        return text
class CsvLogger     (FileLogger     ):
    '''Csv logger.

        Csv File logger.
        Check ``ConsoleLogger`` args.
    '''
            
    def _execute_log(
            self            , 
            level           , 
            log_dict        ,
            log_datetime    ,
            is_one_line     ,
            is_raw          ):
        ConsoleLogger._execute_log(
            self        ,
            level       , 
            log_dict    ,
            log_datetime,
            is_one_line ,
            is_raw      )
        if      not isinstance(log_dict, dict):
            log_dict    = {str(log_dict): ''}
        with open(self._g_path(level),'a') as f :
            writer = csv.writer(f, lineterminator='\n')
            writer.writerows([[
                    log_datetime        ,
                    self.id_      ,
                    level.name          ,
                    key                 ,
                    str(log_dict[key])  ] for key in log_dict])
class SQLLogger     (ConsoleLogger  ):
    '''SQLAlchemy File logger
        
        Dumps the logs to a database, the columns are the same as in the csv 
        generated by ``CsvLogger``

        Params are the same as in ``FileLogger``, excpet a ``sqlalchemy.engine.base.Engine`` is 
        needed instead of a path

        The logger takes care of creating the tables if they don't exist.

        If is_overwrite is set to true, the tables are deleted and created again on each run.

        Args:
            engine      (sqlalchemy.engine.base.Engine  ): The SQLAlchemy engine instance.
    '''

    EasyObj_PARAMS  = OrderedDict((
        ('is_overwrite'        , {'default': False},),
        ('is_combine'          , {'default': False},),
        ('engine_builder'   , {
            'type'      : SQLAlchemyEBuilder    },),))

    def _on_init    (
        self    ):
        super()._on_init()
        self.engine = self.engine_builder.engine
        base = declarative_base()
        self.tables = {}
                
        if self.is_combine:
            _class = type(
                '{}_{}'.format(self.id_, 'is_combined')  ,
                (base,                                      ),
                {   
                    '__tablename__'   : '{}_{}'.format(self.id_, 'is_combined'),
                    'id'              : Column(Integer, primary_key=True)   ,
                    'level'           : Column(String(50))                  , 
                    'log_datetime'    : Column(String(50))                  ,
                    'title'           : Column(String(50))                  ,        
                    'message'         : Column(String(1000))                })  
            self.tables['is_combined'] = _class

        else:
            for level in Level :
                _class = type(
                    '{}_{}'.format(self.id_, level.name)  ,
                    (base,                                      ),
                    {   
                        '__tablename__'   : '{}_{}'.format(self.id_, level.name),
                        'id'              : Column(Integer, primary_key=True)   ,
                        'log_datetime'    : Column(String(50))                  ,
                        'title'           : Column(String(50))                  ,        
                        'message'         : Column(Text())                      }) 
                self.tables[level.name] = _class 

        if self.is_overwrite:
            for table in self.tables.values():
                try :
                    table.__table__.drop(self.engine)
                except OperationalError :
                    pass
        
        base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind= self.engine)()
    def _execute_log(
            self            , 
            level           , 
            log_dict        ,
            log_datetime    ,
            is_one_line     ,
            is_raw          ):
        super()._execute_log(
            level       , 
            log_dict    ,
            log_datetime,
            is_one_line ,
            is_raw      )
        if      not isinstance(log_dict, dict)    :
                log_dict = {log_dict: ''}
        
        for key in log_dict:
            if self.is_combine:
                row = self.tables['is_combined'](
                    log_datetime= log_datetime          ,
                    level       = level.name            ,
                    title       = key                   ,
                    message     = str(log_dict[key])    )
                
            else:
                row = self.tables[level.name](
                    log_datetime= log_datetime          ,
                    title       = key                   ,
                    message     = str(log_dict[key])    )
            self.session.add(row)
        self.session.commit()

############################################################
#################### Exceptions
############################################################

MAIN_LOGGER = DummyObj() 

def set_main_logger(
    logger          , 
    erase   = False , 
    stop    = True  , 
    start   = True  ):
    '''Sets a global logger for all exceptions.
        
        Sets a global exception logger for all exceptions.
        
        This global exception logger will be used if no logger 
        is provided to a wrapper.
        
        Args:
            logger  (Logger ): A Logger instance. 
    '''
    global MAIN_LOGGER
    if      not (
                isinstance(MAIN_LOGGER, DummyObj)   or\
                erase                                   ):
            return 
    if      MAIN_LOGGER  and stop   :
            MAIN_LOGGER.stop()
    MAIN_LOGGER = logger
    if      start                   :
            MAIN_LOGGER.start()

class ExceptionCritical(Exception):
    '''Raised on critical exceptions.

        Raised if an exception is caught by ``handle_exception`` and the level is critical.
        
        Args:
            id  (str    ): Exception id.
    '''
    def __init__(self, origin):
        self.id = '{}_{}'.format(datetime.now().isoformat(), origin)

def handle_exception(
    level           = Level.CRITICAL,
    is_log          = True          ,
    logger          = None          ,
    default_value   = None          ,
    before          = None          ,
    after           = None          ,
    on_success      = None          ,
    on_failure      = None          ,
    params_exc      = []            ,
    is_log_start    = False         ,
    is_log_end      = False         ,
    params_start    = []            ,
    attempts        = 1             ,
    class_logger    = 'logger'      ):
    '''Wrapper for exception handling.

        An exception handling wrapper(decorator).
        
        Args:
            level           (Level                      : Level.CRITICAL    ): The logging level when an exception occurs, 
                if set to critical, the exception is also raised.
            is_log          (bool                       : True              ): If set to false, no logging is done.
            logger          (Logger                     : None              ): Used to log the traceback.
            default_value   (object                     : None              ): The value to return on exceptions.
            before          (collections.abc.Callable   : None              ): Executed before the function call.
            after           (collections.abc.Callable   : None              ): Excecuted after the function call regardless 
                of success or failure.
            on_success      (collections.abc.Callable   : None              ): Executed only on success.
            on_failure      (collections.abc.Callable   : None              ): Excecuted only on failure.
            params_exc      (list, str                  : None              ): Parameters to log, if None: no parameters are 
                logged, if empty list, all parameters are logged.
            is_log_start    (bool                       : False             ): Logs the function call before starting if set 
                to True.
            is_log_end      (bool                       : False             ): Logs the execution termination if set to True.
            params_start    (list, str                  : []                ): Logs params on start.
            attempts        (int                        : 1                 ): Number of repeated attempts in case of exceptions, 
                0 for an infinite loop. 
            class_logger    (str                        : 'logger'          ): Try to use self.<class_logger> if fn is a method.
    '''
    def _handle_exception(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            
            def do_log(l, d):
                if      not is_log                          :
                    return 
                elif    logger                              :
                    logger.log(l, d)
                elif    class_logger != None                \
                        and len(args) != 0                  \
                        and hasattr(args[0], class_logger)  :
                    getattr(args[0], class_logger).log(l, d)
                else                                        :
                    MAIN_LOGGER.log(l, d)

            def g_params_dict(params_to_log):
                all_params  = inspect.signature(fn).parameters
                params_dict = {}

                for param in all_params:
                    if all_params[param].default != inspect._empty:
                        params_dict[param] = all_params[param].default
                for i in range(len(args))   :
                    params_dict[list(all_params.keys())[i]]     = args[i]
                for kwarg in kwargs         :
                    params_dict[kwarg]                          = kwargs[kwarg]
                
                params_to_log  = params_to_log if params_to_log else params_dict
                params_dict = {x: g_path(params_dict,x, is_return_last= False) for x in params_to_log}

                return {'Parameter: {}'.format(param):  str(params_dict[param]) for param in params_dict}
                
            #Set execution result to fall back value
            return_value = default_value

            name        = '{}.{}'.format(fn.__module__, fn.__qualname__)

            #Execute the before routines
            if before :
                before()

            n_attempt   = 0
            while attempts == 0 or n_attempt < attempts :
                if is_log_start:
                    start_dict = {'Started {}'.format(n_attempt+ 1): name}
                    if params_start != None:
                        start_dict.update(g_params_dict(params_start))
                    do_log(Level.INFO  , start_dict)
                try :
                    #Call the function
                    return_value =  fn(*args,**kwargs)
                except :
                    #Extract traceback
                    exc_type, exc_obj, exc_tb   = sys.exc_info()
                    tbl                         = traceback.extract_tb(exc_tb)
                    tb                          = tbl[1] if len(tbl) > 1 else tbl[0]

                    if exc_type != ExceptionCritical:
                        exc_crt     = ExceptionCritical(name)
                        log_dict    = {
                            'id'        : exc_crt.id                            ,
                            'File'      : tb.filename                           ,
                            'Origin'    : name                                  ,
                            'Type'      : exc_type.__name__                     ,
                            'Line'      : tb.lineno                             ,
                            'Code'      : tb.line                               ,
                            'Msg'       : exc_obj.args[0] if len(exc_obj.args)  \
                                            else ''                             }
                    else :
                        exc_crt     = exc_obj
                        log_dict    = {
                            'id'        : exc_crt.id        ,
                            'catcher'   : name              ,
                            }

                    log_dict['attempt'] = n_attempt+ 1

                    if params_exc != None:
                        log_dict.update(g_params_dict(params_exc))

                    do_log(level, log_dict)

                    #Execute the failure routines
                    if on_failure :
                        on_failure()

                    #If the level is critical, raise, else discard
                    if level == level.CRITICAL:
                        raise exc_crt
                else :
                    if is_log_end:
                        do_log(Level.INFO  ,{'Finished': name})
                    if on_success :
                        on_success()
                    break
                finally :
                    #Execute te after routines
                    if after :
                        after()
                    n_attempt   +=1
            return return_value
        return wrapper
    return _handle_exception