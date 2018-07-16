'''
    A collection of tools.
    by saledddar@gmail.com, 2018.
'''

import requests
import os
import lxml
import traceback
import requests
import operator
import sys

from functools import wraps
from functools import reduce
from enum import Enum
from pyunet import unit_test
from datetime import datetime
from lxml.html import fromstring, HtmlElement
from requests.packages.urllib3.exceptions import InsecureRequestWarning


#Default requests headers
HEADERS={
    'User-Agent':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0',
    }

EXCEPTION_LOGGER = None

#Disable warnings on insecure requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#-------------------------------------------------------------
#   Test code
#-------------------------------------------------------------

TEST_LOG_STR = '''[Date time][logger              ] [INFO    ]:
    Msg                 : A message
    ===================================================================================================='''.replace('\n    ','\n')

TEST_EXC_STR = '''[Date time][logger              ] [ERROR   ]:
    File                : {}
    Origine             : util.custom_test_1
    Type                : ZeroDivisionError
    Line                : 440
    Code                : x = 1/0
    Msg                 : division by zero
    ===================================================================================================='''.format(os.path.abspath(__file__)).replace('\n    ','\n')

def read_file(path):
    '''
        Returns the content of a file.
    '''
    with open(path) as f :
        data = f.read()
    return data

class datetime_mock():
    '''
        A mock to the datetime module.
    '''
    def now():
        return datetime_mock()

    def strftime(self, x):
        return 'Date time'

SAVE_DATETIME = datetime

def before_test_strftime():
    '''
        Creates a mock for strftime
    '''
    global datetime
    datetime        = datetime_mock

def after_test_strftime():
    '''
        Removes a mock for strftime
    '''
    global datetime
    datetime       = SAVE_DATETIME

#-------------------------------------------------------------
#   Logging and Exceptions
#-------------------------------------------------------------

class Level(Enum):
    '''
        Logging levels
    '''
    DEBUG       = 1
    INFO        = 2
    WARN        = 3
    ERROR       = 4
    CRITICAL    = 5

class Logger():
    '''
        Logger base, prints logs on console.
        Instance    :
            name        : The name of the logger.
            print_log   : Prints the log on the console if set to True.
    '''
    def __init__(self, name= 'logger', print_log= False):
        self.name       = name
        self.print_log  = print_log

    @unit_test(
        [
            {
            'before': before_test_strftime,
            'after' : after_test_strftime,
            'args'  : [Level.INFO] ,
            'assert': TEST_LOG_STR},
        ]
        )
    def log(self, level= Level.INFO, log_dict= {'Msg': 'A message'}):
        '''
            Simple logging, prints the level and msg to the screen.
            Args    :
                level       : Logging level.
                log_dict    : Contians a dict with logs values.
            Returns : The log.
        '''
        dict_text   = '\n'.join(['{:<20}: {}'.format(k,v) for k,v in log_dict.items()])
        text        = '[{}][{:<20}] [{:<8}]:\n{}'.format(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),self.name, level.name, dict_text)+'\n'+'='*100
        if self.print_log :
            print(text)
        return text

class FileLogger(Logger):
    '''
        File logger
        Instance    :
            name        : The name of the logger.
            root        : The root directory to save the logs.
            print_log   : Prints the log on the console if set to True.
            overwrite   : If True, always erase previous logs on instance creation.
    '''
    def __init__(self, name= 'logger', root= 'logs', print_log= False, overwrite= True):
        super().__init__(name= name, print_log= print_log)
        self.root       = root
        self.print_log  = print_log
        self.overwrite  = overwrite

        self.create_files()

    @unit_test(
        [
            {
            'assert': lambda x: os.path.isfile(os.path.join('logs','logger','INFO.log')) }
        ]
        )
    def create_files(self):
        '''
            Creates the files needed to save logs.
        '''
        logs_path   = os.path.join(self.root, self.name)
        #Check and create the root directory
        if not os.path.isdir(logs_path):
            os.makedirs(logs_path)

        #Check all log levels files:
        for level in Level :
            path    = os.path.join(logs_path, level.name+ '.log')
            if self.overwrite:
                open(path, 'w').close()

    @unit_test(
        [
            {
            'before': before_test_strftime,
            'after' : after_test_strftime,
            'kwargs': {'log_dict':{'Msg': 'A message'}},
            'assert': lambda x: TEST_LOG_STR+'\n' == read_file(os.path.join('logs','logger','INFO.log'))}
        ]
        )
    def log(self, level= Level.INFO, log_dict= {'Msg': 'A message'}):
        '''
            Logs the msg into a file.
            Args    :
                level       : The log level.
                log_dict    : Contians a dict with logs values.
            Returns : The log text.
        '''
        text    = super().log(level = level, log_dict= log_dict)
        path    = os.path.join(self.root, self.name, level.name+ '.log')
        with open(path,'a') as f :
            f.write(text+'\n')
        return text

def handle_exception(
    level           = Level.ERROR   ,
    fall_back_value = None          ,
    before          = None          ,
    after           = None          ,
    on_success      = None          ,
    on_failure      = None          ,
    ):
    '''
        An exception handling wrapper(decorator).
        Args    :
            level           : The logging level when an exception occurs, if set to critical, the exception is also raised.
            logger          : Used to log the traceback.
            fall_back_value : The value to return on exceptions.
            before          : Executed before the function call.
            after           : Excecuted after the function call regardless the success or failure.
            on_success      : Executed only on success.
            on_failure      : Excecuted only on failure.
    '''
    def _handle_exception(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            #Set execution result to fall back value
            res = fall_back_value

            #Execute the before routines
            if before :
                before()

            try :
                #Call the function
                res =  fn(*args,**kwargs)
            except :
                #Extract traceback
                exc_type, exc_obj, exc_tb   = sys.exc_info()
                tb                          = traceback.extract_tb(exc_tb)[-1]

                #Checks if the function is a mehtod and should have the self argument passed
                try :
                    is_method   = inspect.getargspec(fn)[0][0] == 'self'
                except :
                    is_method   = False

                #Builds the name of the method,module.class.method or module.method
                if is_method :
                    class_name  = str(fn).split()[1].split('.')[0]
                    name        = '{}.{}.{}'.format(fn.__module__, class_name, fn.__name__)
                else :
                    name        = '{}.{}'.format(fn.__module__, fn.__name__)
                log_dict = {
                    'File'      : exc_tb.tb_frame.f_code.co_filename    ,
                    'Origine'   : name                                  ,
                    'Type'      : exc_type.__name__                     ,
                    'Line'      : tb[-3]                                ,
                    'Code'      : tb[-1]                                ,
                    'Msg'       : exc_obj.args[0]                       ,
                    }

                #Execute the failure routines
                if on_failure :
                    on_failure()

                #If log, save the logs
                if EXCEPTION_LOGGER:
                    EXCEPTION_LOGGER.log(level,log_dict)

                #If the level is critical, raise, else discard
                if level == level.CRITICAL:
                    raise
            else :
                if on_success :
                    on_success()
            finally :
                #Execute te after routines
                if after :
                    after()
            return res
        return wrapper
    return _handle_exception

#-------------------------------------------------------------
#   Tools
#-------------------------------------------------------------

@handle_exception(level=Level.CRITICAL)
@unit_test(
    [
        {
        'args'  : ['folder1','folder2','file.txt'] ,
        'assert': os.path.join(os.path.dirname(os.path.realpath(__file__)),'folder1','folder2','file.txt')}
    ])
def create_path_in_script_directory(*args):
    '''
        Generates a path in the directory of the script.
        If the relative paht doesn't exist, it is created
        Args    :
            *args       : relative path.
    '''
    #If the file name is a path
    file_name = os.path.join(*args)

    #Get the script file path
    script_file_path=os.path.realpath(__file__)

    #Gpthe directory path
    script_directory=os.path.dirname(script_file_path)

    #Make sure directory exists if nested
    directory =os.path.join(script_directory,os.path.dirname(file_name))
    if not os.path.exists(directory):
        os.makedirs(directory)

    #Build the file path using the file name and the directory path
    file_path=os.path.join(script_directory,file_name)

    #return
    return file_path

@handle_exception(level=Level.CRITICAL)
@unit_test(
    [
        {
        'args'  : ['<a>A link</a>','//a/text()'] ,
        'assert': ['A link'] }
    ])
def find_xpath(element,xpath):
    '''
        Evaluate an xpath expression and returns the result
        Args    :
            element : Can be either a raw html/xml string or a n lxml element
            xpath   : xpath expression
        Returns :
            An array of strings
    '''
    #If the element is a raw html text, create an lxml tree
    if type(element) is not HtmlElement :
        result = fromstring(element).xpath(xpath)
    #Else, evaluate the expression
    else :
        result = fromstring(etree.tostring(element)).xpath(xpath)
    return result

@handle_exception(level=Level.CRITICAL)
@unit_test(
    [
        {
        'args'  : [[' a ','b ',' c']] ,
        'assert': 'a, b, c' }
    ])
def join_array_text(array,join_str=', '):
    '''
        Joins and adjusts a text array.
        Args    :
            array   : an array returned afer evaluating an xpath expression
        Returns :
            A single string
    '''
    return join_str.join([ x.strip() for x in array if x.strip() != ''])

@handle_exception(level=Level.CRITICAL)
@unit_test(
    [
        {
        'args'  : ['https://api.ipify.org/'] ,
        'assert': lambda x : len(x.text.split('.'))== 4}
    ])
def do_request(url, params =None, is_post =False, is_json= False ,headers= HEADERS, logger= None):
    '''
        A nice wrapper for the requests module
        Args    :
            url         : request url
            params      : this can be either get, post or json data
            is_post     : True if post request
            is_json     : True if josn request
            headers     : headers if needed
    '''
    #Log the request if log is enabled
    if logger:
        logger.log(Level.INFO,{'Request': url,'Method': 'POST' if is_post else 'GET'})

    #a json request
    if params and is_json :
        r = requests.post(url, json= params, verify= False)

    #A post request
    elif params and is_post:
        r = requests.post(url, headers= headers,data = params, verify= False)

    #A get request with params
    elif params :
        r = requests.get(url, headers =headers, params= urlencode(params), verify= False)

    #A simple get request
    else :
        r = requests.get(url, headers =headers, verify =False)

    #Return the response
    return r

@handle_exception(level=Level.ERROR)
@unit_test(
    [
        {
        'args'  : [{'a':{'b':{'c':'value'}}},['a','b','c']] ,
        'assert': 'value' }
    ])
def dict_path(nested_dict, path):
    '''
        Gets the value in path from the nested dict.
        Args    :
            nested_dict : A python dict.
            path        : The path to the value.
        Returns :
            The value
    '''
    return reduce(operator.getitem, path, nested_dict)

@unit_test(
    [
        {
        'args'  : [{1: 'a'},1] ,
        'assert': 'a' },
        {
        'args'  : [['a','b','c'],2] ,
        'assert': 'c' },
        {
        'args'  : [['a','b','c'],5]}
    ])
@handle_exception(level=Level.ERROR,fall_back_value=None)
def safe_getitem(array_or_dict, key=0):
    '''
        Gets an element from a dict or an array, return None if the key is not found or out of range.
        Args    :
            array_or_dict   : The array or dict to look into.
            key             : The key to look for.
        Returns : The value if found else none.
    '''
    return array_or_dict[key]
