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

#Disable warnings on insecure requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#-------------------------------------------------------------
#   Test methods
#-------------------------------------------------------------
def read_file(path):
    '''
        Returns the content of a file.
    '''
    with open(path) as f :
        data = f.read()
    return data

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
            name        : The name of the logger
    '''
    def __init__(self, name= 'logger'):
        self.name = name

    @unit_test(
        [
            {
            'args'  : [Level.CRITICAL, 'A message'] ,
            'assert': '[{}][{:<20}] [{:<8}]: {}'.format(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),'logger', 'CRITICAL', 'A message')+'\n'+'='*100},
        ]
    )
    def log(self, level= Level.INFO, msg= 'Test message', print_log= False):
        '''
            Simple logging, prints the level and msg to the screen.
            Args    :
                level       : Logging level.
                msg         : Message to log.
                print_log   : Prints the log on the console if set to True.
            Returns : The log.
        '''
        text = '[{}][{:<20}] [{:<8}]: {}'.format(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),self.name, level.name, msg)+'\n'+'='*100
        if print_log :
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
        super().__init__(name= name)
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
            'kwargs': {'msg': 'A message'},
            'assert': lambda x: '[{}][{:<20}] [{:<8}]: {}'.format(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),'logger', 'INFO', 'A message')+ '\n'+ ('='*100)+ '\n' \
                                            == read_file(os.path.join('logs','logger','INFO.log'))}
        ]
    )
    def log(self, level= Level.INFO, msg= 'Test message'):
        '''
            Logs the msg into a file.
            Args    :
                level   : The log level.
                msg     : The message to log.
            Returns : The log.
        '''
        text    = super().log(level = level, msg= msg, print_log= self.print_log)
        path    = os.path.join(self.root, self.name, level.name+ '.log')
        with open(path,'a') as f :
            f.write(text+'\n')
        return text

def handle_exception(
    level           = Level.ERROR   ,
    logger          = Logger()      ,
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
        def wrapper_handle_exception(*args, **kwargs):
            #Set execution result to fall back value
            res = fall_back_value

            #Execute the before routines
            if before :
                before()

            try :
                #Call the function
                res =  fn(*args,**kwargs)
            except :
                #Extract the exception informations :
                exception_info = '\n>>> '.join([x.strip() for x  in traceback.format_exc().split('\n')[1:] if x.strip()!=''])

                #Execute the failure routines
                if on_failure :
                    on_failure()

                #If log, save the logs
                if logger:
                    logger.log(level,'{} : {}'.format(fn.__name__,exception_info+'\n'))

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
        return wrapper_handle_exception
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
        logger.log(Level.INFO,'[REQUEST {}] : {}'.format('POST' if is_post else 'GET',url))

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
