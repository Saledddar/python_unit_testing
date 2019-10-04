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
from    sqlalchemy                  import  Column          , Integer   , String
from    sqlalchemy.exc              import  OperationalError
from    sqlalchemy.orm              import  sessionmaker
from    functools                   import  wraps   , reduce
from    collections                 import  OrderedDict
from    collections.abc             import  Callable
from    datetime                    import  datetime
from    threading                   import  Thread
from    enum                        import  Enum

from    .common                     import  EasyObj
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
            _id         (str)   : The id of the logger, must be unique when running multiple loggers.
            print_log   (bool)  : Prints the log on the console if True.
    '''
    
    LIVE_LOGGERS    = []
    EasyObj_PARAMS          = OrderedDict((
        ('_id' , {
            'default': 'sal-logger' },),))
    
    @staticmethod
    @atexit.register
    def stop_all():
        '''Stop all live loggers.

            Stops all loggers regestered at LIVE_LOGGERS
        '''
        for logger in Logger.LIVE_LOGGERS.copy():
            logger.stop()
      
    def __enter__   (self):
        self.start()
        return self
    def __exit__    (
        self        , 
        type        , 
        value       , 
        traceback   ):
        self.stop()

    def _on_init(
        self    ):
        self.queue      = queue.Queue()
        self.is_alive   = False

        for level in Level :
            setattr(self, level.name.lower(), lambda x, l= level: self.log(l, x))
    
    def loop        (
        self    ):
        '''Logging loop.

            Keeps looping!
        '''
        while True:
            item = self.queue.get()
            if item == 'EXIT_LOGGER_SIGNAL':
                break
            else :
                self.execute_log(*item)
          
        self.execute_log(
            level       = Level.INFO                                                ,
            log_dict    = {'Logger stopped': 'Logger stopped!'} ,
            log_datetime= datetime.now().isoformat())
    def log         (
        self        ,      
        level       , 
        log_dict    ):
        '''Log the logs.

            Pushes the log to the logging queue.
            
            Args    :
                level   (Level) : The logging level.
                log_dict(dict)  : The logging dict.
        '''

        self.queue.put([
                level                       ,
                log_dict                    ,
                datetime.now().isoformat()  ])
    def start       (
        self    ):
        '''Start loging.
        
            Starts the logging thread (self.loop)
        '''
        if self.is_alive:
            return 
        self.is_alive = True
        self.thread = Thread(
            name    = self._id  , 
            target  = self.loop , 
            daemon  = True      ) 
        self.thread.start()

        self.log(
            level   = Level.INFO                            ,
            log_dict= {'Logger started': 'Logger started!'} )
        
        if self not in Logger.LIVE_LOGGERS:
            Logger.LIVE_LOGGERS.append(self)
    def stop        (
        self    ):
        '''Stop!

            No more trees are cut, Saving the planet!.
        '''
        if not self.is_alive:
            return 

        self.log(
            level   = Level.INFO                            ,
            log_dict= {'Logger stop signal': 'Logger stoping signal received!'} )   
        
        #Wait for the logger to log the remaining logs
        self.queue.put('EXIT_LOGGER_SIGNAL')
        self.thread.join()
        self.is_alive  = False 

        if self in Logger.LIVE_LOGGERS:
            Logger.LIVE_LOGGERS.remove(self)
    def execute_log (
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
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
class ConsoleLogger (Logger         ):
    '''Console logger.
        A simple console logger, prints the logs on console.
    '''
    EasyObj_PARAMS  = OrderedDict((
        ('print_log', {'default': True }),
        ('one_line' , {'default': True })))
    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):

        if      self.one_line   :
            dict_text   = '|'.join(['{}, {}'.format(k, v) for k, v in log_dict.items()])
            text        = '[{}][{:<20}] [{:<8}]:{}'.format(
                log_datetime                ,
                self._id              , 
                level.name                  , 
                dict_text                   )
        else                    :
            format_message  = lambda message: '\n'+ '\n'.join(textwrap.wrap(
                        message                         , 
                        subsequent_indent   = '\t\t'    , 
                        initial_indent      = '\t\t'    , 
                        width               = 100       , 
                        break_on_hyphens    = True      )) 

            dict_text   = '\n'.join(
                ['\t{:<20}:{}'.format(
                    k,
                    format_message(str(v))) for k,v in log_dict.items()])

            text        = '[{}][{:<20}] [{:<8}]:\n{}'.format(
                log_datetime                ,
                self._id              , 
                level.name                  , 
                dict_text                   )+'\n'+'='*120

        if self.print_log :
            print(text)

        return text
class FileLogger    (ConsoleLogger  ):
    '''Text file logger.

        Simple text file logger based on ``ConsoleLogger``, dumps the logs generated by ``ConsoleLogger`` to txt files.

        Args:
            root        (str    ): The root directory to save the logs, logs will be saved under 
                                  root/_id.
            overwrite   (bool   ): If True, always erase previous logs on instance creation.
            combine     (bool   ): If True, all levels are combined in one file ``combined.log``.
    '''

    EasyObj_PARAMS  = OrderedDict((
        ('overwrite', {'default': False}),
        ('combine'  , {'default': True }),
        ('root'     , {'default': '.'}  )))
    

    def _on_init(self):
        logs_path   = os.path.join(self.root, self._id)
        #Check and create the root directory
        if not os.path.isdir(logs_path):
            os.makedirs(logs_path)

        #Check all log levels files:
        if not self.combine and self.overwrite:
            for level in Level :
                path    = os.path.join(logs_path, level.name+ '.log')
                open(path, 'w').close()

        elif self.combine and self.overwrite:
            path    = os.path.join(logs_path, 'combined'+ '.log')
            open(path, 'w').close()

    def g_path(self, level):
        '''Correct logging path for ``level``.

            Get the correct file path to save the log
            
            Args:
                level   (Level) : The log level.
            
            Returns:
                str     : Logging file path. 
        '''
        return os.path.join(
            self.root                                           , 
            self._id                                      , 
            ('combined' if self.combine else level.name)+ '.log')

    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        text    = super().execute_log(
            level       , 
            log_dict    ,
            log_datetime)

        with open(self.g_path(level),'a') as f :
            f.write(text+'\n')
        return text
class CsvLogger     (FileLogger     ):
    '''Csv logger.

        Csv File logger.
        Check ``ConsoleLogger`` args.
    '''
            
    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        ConsoleLogger.execute_log(
            self        ,
            level       , 
            log_dict    ,
            log_datetime)

        with open(self.g_path(level),'a') as f :
            writer = csv.writer(f, lineterminator='\n')
            writer.writerows([[
                    log_datetime        ,
                    self._id      ,
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

        If overwrite is set to true, the tables are deleted and created again on each run.

        Args:
            engine      (sqlalchemy.engine.base.Engine  ): The SQLAlchemy engine instance.
    '''

    EasyObj_PARAMS  = OrderedDict((
        ('overwrite'        , {'default': False},),
        ('combine'          , {'default': False},),
        ('engine_builder'   , {
            'type'      : SQLAlchemyEBuilder    ,
            'default'   : SQLAlchemyEBuilder()  },),))

    def _on_init(self):
        super()._on_init()
        self.engine = self.engine_builder.engine
        base = declarative_base()
        self.tables = {}
                
        if self.combine:
            _class = type(
                '{}_{}'.format(self._id, 'combined')  ,
                (base,                                      ),
                {   
                    '__tablename__'   : '{}_{}'.format(self._id, 'combined')    ,
                    'id'              : Column(Integer, primary_key=True)             ,
                    'log_datetime'    : Column(String)                                ,
                    'level'           : Column(String)                                , 
                    'title'           : Column(String)                                ,        
                    'message'         : Column(String)                                }) 
            self.tables['combined'] = _class

        else:
            for level in Level :
                _class = type(
                    '{}_{}'.format(self._id, level.name)  ,
                    (base,                                      ),
                    {   
                        '__tablename__'   : '{}_{}'.format(self._id, level.name)    ,
                        'id'              : Column(Integer, primary_key=True)             ,
                        'log_datetime'    : Column(String)                                ,
                        'title'           : Column(String)                                ,        
                        'message'         : Column(String)                                }) 
                self.tables[level.name] = _class 

        if self.overwrite:
            for table in self.tables.values():
                try :
                    table.__table__.drop(self.engine)
                except OperationalError :
                    pass
        
        base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind= self.engine)()
         
    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        super().execute_log(
            level       , 
            log_dict    ,
            log_datetime)

        for key in log_dict:
            if self.combine:
                row = self.tables['combined'](
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

class DummyLogger(EasyObj):
    CALLABLES   =  [x for x in dir(Logger()) if             \
                isinstance(getattr(Logger(), x), Callable)  ]

    def __getattr__(self, name):
        if      name in self.CALLABLES   :
            return lambda *args, **kwargs: None             
        else                        :
            return None

############################################################
#################### Exceptions
############################################################

MAIN_LOGGER = DummyLogger() 

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
                isinstance(MAIN_LOGGER, DummyLogger) or\
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
                params_dict = {x: g_path(params_dict,x) for x in params_to_log}

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