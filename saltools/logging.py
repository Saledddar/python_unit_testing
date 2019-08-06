from    sqlalchemy.ext.declarative  import  declarative_base
from    sqlalchemy                  import  Column          , Integer   , String
from    sqlalchemy.exc              import  OperationalError
from    sqlalchemy.orm              import  sessionmaker
from    functools                   import  wraps   , reduce
from    collections                 import  OrderedDict
from    datetime                    import  datetime
from    threading                   import  Thread
from    enum                        import  Enum
from    time                        import  sleep

from    .common                     import  EasyObj

import  traceback
import  textwrap
import  atexit
import  queue
import  sys
import  csv
import  os

############################################################
#################### Logging
############################################################

class Level(Enum):
    '''
        Logging levels
    '''
    DEBUG       = 1
    INFO        = 2
    WARN        = 3
    ERROR       = 4
    CRITICAL    = 5

class Logger(EasyObj):
    '''
        Logger base.
        All derived must override on_init and execute_log.
        Args    :
            logger_id   (str)   : The id of the logger, must be unique when running multiple loggers.
            print_log   (bool)  : Prints the log on the console if True.
    '''
    
    LIVE_LOGGERS    = []
    EasyObj_KWARGS          = OrderedDict((
        ('logger_id' , {'default': 'sal-logger' }   ),
        ('print_log' , {'default': True         }   )))
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.queue  = queue.Queue()
        self.alive  = False
        self.thread = Thread(target= self.loop, daemon= True) 
        self.sleep  = 0.5

        for level in Level :
            setattr(self, level.name.lower(), lambda x: self.log(level, x))

        self.on_init()

    def __enter__(self):
        '''
            Implements __enter__ fro "with" statement.
        '''
        self.start()
        return self

    def __exit__(
        self        , 
        type        , 
        value       , 
        traceback   ):
        '''
            Implements __exit__ for "with" statement.
        '''
        self.stop()

    def loop(self):
        '''
            Logging loop.
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

    def log(
        self        ,      
        level       , 
        log_dict    ):
        '''
            Pushes the log to the logging queue.
            Args    :
                level   (Level) : The logging level.
                log_dict(dict)  : The logging dict.
        '''

        self.queue.put([
                level                       ,
                log_dict                    ,
                datetime.now().isoformat()  ])

    def start(self):
        '''
            Starts the logging thread (self.loop)
        '''
        if self.alive:
            return 
        self.alive = True
        self.thread.start()

        self.log(
            level   = Level.INFO                            ,
            log_dict= {'Logger started': 'Logger started!'} )
        
        #Wait for the logger ot log the first logs
        sleep(self.sleep)

        if self not in Logger.LIVE_LOGGERS:
            Logger.LIVE_LOGGERS.append(self)

    def stop(self):
        '''
            Stop the logging process.
        '''
        if not self.alive:
            return 

        self.log(
            level   = Level.INFO                            ,
            log_dict= {'Logger stop signal': 'Logger stoping signal received!'} )   
        
        #Wait for the logger to log the remaining logs
        self.queue.put('EXIT_LOGGER_SIGNAL')
        self.thread.join()
        self.alive  = False 

        if self in Logger.LIVE_LOGGERS:
            Logger.LIVE_LOGGERS.remove(self)
    
    @staticmethod
    @atexit.register
    def stop_all():
        '''
            Stops all loggers regestered at LIVE_LOGGERS
        '''
        for logger in Logger.LIVE_LOGGERS.copy():
            logger.stop()

    def on_init(self):
        '''
            Will be executed in __init__, contains logic to 
            set up the environment for the logger.
            Must be overridden by derived classes.
        '''
        raise NotImplementedError()

    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        '''
            Defines the logging logic set by the derived logger class.
            Must be overridden by all derived classes.
            Args    :
                level       (Level)     : Logging level.
                log_dict    (dict)      : Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime)  : The date of the log in iso format.
            Returns : 
                str         : The log string.
        '''
        raise NotImplementedError()

class ConsoleLogger(Logger):
    '''
        A simple console logger, prints the logs on console.
    '''

    def on_init(self):
        '''
            Nothing to see here, moving on!
        '''
        pass

    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        '''
            Simple logging, prints the level and msg to the screen.
            Args    :
                level       (Level)     : Logging level.
                log_dict    (dict)      : Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime)  : The date of the log in iso format.
            Returns : 
                str         : The log string.
        '''

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
            self.logger_id              , 
            level.name                  , 
            dict_text                   )+'\n'+'='*116

        if self.print_log :
            print(text)

        return text

class FileLogger(ConsoleLogger):
    '''
        Simple File logger based on ConsoleLogger, dumps the logs to txt files.
        Args    :
            root        (str)   : The root directory to save the logs, logs will be saved under 
                                    root/logger_id.
            overwrite   (bool)  : If True, always erase previous logs on instance creation.
            combine     (bool)  : If True, all levels are combined in one file
    '''

    EasyObj_KWARGS  = OrderedDict((
        ('overwrite', {'default': False}),
        ('combine'  , {'default': True }),
        ('root'     , {'default': '.'}  )))
    

    def on_init(self):
        '''
            Creates the files needed to save logs.
        '''
        logs_path   = os.path.join(self.root, self.logger_id)
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
        '''
            Get the correct file path to save the log
            Args    :
                level   (Level) : The log level.
            Returns :
                (str)   : Logging file path. 
        '''
        return os.path.join(
            self.root                                           , 
            self.logger_id                                      , 
            ('combined' if self.combine else level.name)+ '.log')

    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        '''
            Simple file logging, dumps the logs into a text file.
            Args    :
                level       (Level)     : Logging level.
                log_dict    (dict)      : Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime)  : The date of the log in iso format.
            Returns : 
                str     : The log string.
        '''
        text    = super().execute_log(
            level       , 
            log_dict    ,
            log_datetime)

        with open(self.g_path(level),'a') as f :
            f.write(text+'\n')
        return text

class CsvLogger(FileLogger):
    '''
        Csv File logger.
        Args    :
            logger_id   (str)   : Logger id, must be unique when using multiple loggers.
            print_log   (bool)  : Prints the log on the console if True.
            root        (str)   : The root directory to save the logs, logs will be saved under 
                                    root/logger_id.
            overwrite   (bool)  : If True, always erase previous logs on instance creation.
            combine     (bool)  : If True, all levels are combined in one file
    '''
            
    def execute_log(
            self        , 
            level       , 
            log_dict    ,
            log_datetime):
        '''
            Csv file logging, dumps the logs into a csv file.
            Args    :
                level       (Level)     : Logging level.
                log_dict    (dict)      : Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime)  : The date of the log in iso format.
            Returns : 
                str     : The log string.
        '''
        ConsoleLogger.execute_log(
            self        ,
            level       , 
            log_dict    ,
            log_datetime)

        with open(self.g_path(level),'a') as f :
            writer = csv.writer(f, lineterminator='\n')
            writer.writerows([[
                    log_datetime        ,
                    self.logger_id      ,
                    level.name          ,
                    key                 ,
                    str(log_dict[key])  ] for key in log_dict])

class SQLAlchemyLogger(Logger):
    '''
        SQLAlchemy File logger
        Args    :
            logger_id   (str)                           : Logger id, must be unique when using multiple loggers.
            print_log   (bool)                          : Prints the log on the console if set to True.
            overwrite   (bool)                          : If True, always erase tables on instance creation.
            combine     (bool)                          : If True, all levels are combined into one table.
            engine      (sqlalchemy.engine.base.Engine) : The SQLAlchemy engine instance.
    '''

    EasyObj_KWARGS  = OrderedDict((
        ('overwrite', {'default': False}),
        ('combine'  , {'default': False}),
        ('engine'   , {}                )))

    def on_init(self):
        '''
            Creates the files needed to save logs.
        '''
        base = declarative_base()
        self.tables = {}
                
        if self.combine:
            _class = type(
                '{}_{}'.format(self.logger_id, 'combined')  ,
                (base,                                      ),
                {   
                    '__tablename__'   : '{}_{}'.format(self.logger_id, 'combined')    ,
                    'id'              : Column(Integer, primary_key=True)             ,
                    'log_datetime'    : Column(String)                                ,
                    'level'           : Column(String)                                , 
                    'title'           : Column(String)                                ,        
                    'message'         : Column(String)                                }) 
            self.tables['combined'] = _class

        else:
            for level in Level :
                _class = type(
                    '{}_{}'.format(self.logger_id, level.name)  ,
                    (base,                                      ),
                    {   
                        '__tablename__'   : '{}_{}'.format(self.logger_id, level.name)    ,
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
        '''
            SQLAlchemy logging, dumps the logs into a database.
            Args    :
                level       (Level)     : Logging level.
                log_dict    (dict)      : Contains a dict with title-or-tag/log key/value
                                            this helps sorting logs by tag if needed.
                log_datetime(datetime)  : The date of the log in iso format.
            Returns : 
                str     : The log string.
        '''
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

############################################################
#################### Exceptions
############################################################

EXCEPTION_LOGGER = None

def set_logger(logger):
    '''
        Sets a global exception logger for all exceptions.
        This global exception logger will be used if no logger 
            is provided to a wrapper.
        Args    :
            logger  : A Logger instance. 
    '''
    global EXCEPTION_LOGGER
    if not EXCEPTION_LOGGER:
        EXCEPTION_LOGGER = logger

class ExceptionCritical(Exception):
    '''
        An exception to raise if an exception is caught and the level is critical.
        Instance    :
            id  : Exception id.
    '''
    def __init__(self, origin):
        self.id = '{}_{}'.format(datetime.now().isoformat(), origin)

def handle_exception(
    level           = Level.CRITICAL,
    log             = True          ,
    logger          = None          ,
    fall_back_value = None          ,
    before          = None          ,
    after           = None          ,
    on_success      = None          ,
    on_failure      = None          ,
    log_args        = True          ,
    log_start       = False         ,
    log_end         = False         ):
    '''
        An exception handling wrapper(decorator).
        Args    :
            level           : The logging level when an exception occurs, if set to critical, the exception is also raised.
            log             : If set to false, no logging is done.
            logger          : Used to log the traceback.
            fall_back_value : The value to return on exceptions.
            before          : Executed before the function call.
            after           : Excecuted after the function call regardless of success or failure.
            on_success      : Executed only on success.
            on_failure      : Excecuted only on failure.
            log_args        : Logs args if set to True.
            log_start       : Logs the function call before starting if set to True.
            log_end         : Logs the execution termination if set to True.
    '''
    def _handle_exception(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            #Set execution result to fall back value
            return_value = fall_back_value

            name        = '{}.{}'.format(fn.__module__, fn.__qualname__)

            #Execute the before routines
            if before :
                before()
            if log and log_start:
                if logger:
                    logger.log(
                        Level.INFO  ,
                        {'Started': name})
                elif EXCEPTION_LOGGER:
                    EXCEPTION_LOGGER.log(
                        Level.INFO  ,
                        {'Started': name})

            try :
                #Call the function
                return_value =  fn(*args,**kwargs)
            except :
                #Extract traceback
                exc_type, exc_obj, exc_tb   = sys.exc_info()
                tb                          = traceback.extract_tb(exc_tb)[-1]

                if exc_type != ExceptionCritical:
                    exc_crt     = ExceptionCritical(name)
                    log_dict    = {
                        'id'        : exc_crt.id                            ,
                        'File'      : tb.filename                           ,
                        'Origin'    : name                                  ,
                        'Type'      : exc_type.__name__                     ,
                        'Line'      : tb.lineno                             ,
                        'Code'      : tb.line                               ,
                        'Msg'       : exc_obj.args[0]                       }
                else :
                    exc_crt     = exc_obj
                    log_dict    = {
                        'id'        : exc_crt.id        ,
                        'catcher'   : name              ,
                        }
                for i in range(len(args)) :
                    log_dict['arg_{}'.format(i)]= str(args[0])
                
                i   = 0 
                for kwarg in kwargs :
                    log_dict['kwarg_{}_{}'.format(i, kwarg)]= str(kwargs[kwarg])
                    i   +=1

                #Execute the failure routines
                if on_failure :
                    on_failure()

                #If loggers
                if log and logger:
                    logger.log(level,log_dict)
                elif log and EXCEPTION_LOGGER:
                    EXCEPTION_LOGGER.log(level,log_dict)

                #If the level is critical, raise, else discard
                if level == level.CRITICAL:
                    raise exc_crt
            else :
                if log and log_end:
                    if logger:
                        logger.log(
                            Level.INFO  ,
                            {'Finished': name})
                    elif EXCEPTION_LOGGER:
                        EXCEPTION_LOGGER.log(
                            Level.INFO  ,
                            {'Finished': name})
                if on_success :
                    on_success()
            finally :
                #Execute te after routines
                if after :
                    after()
            return return_value
        return wrapper
    return _handle_exception

