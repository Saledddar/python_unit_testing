'''Wen utilities.

    Web utilities.
'''
from    lxml.html       import  fromstring      , HtmlElement
from    .logging        import  handle_exception, Level
from    .misc           import  g_path
from    urllib.parse    import  urlencode       , urlparse      , parse_qs

import  requests
import  lxml

requests.packages.urllib3.disable_warnings()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'} 

def g_url_param (
    url             ,
    param   = None  ,
    is_list = False ):
    '''Gets the value of given encoded param.

        Args:
            url     (str    ): URL to decode.
            param   (str    ): Param name, If None, will return all param names and values.
            is_list (bool   ): Is the parameter value is a list(usually separated by commas).
        Returns:
            dict|object : The value of the param or a dict of pram-names/values.
    '''
    query   = urlparse(url).query
    path    = [param]+([] if is_list else [0])
    return  g_path(parse_qs(query), path, is_return_last= True)
def do_request  (
    url                     , 
    params      = None      , 
    is_post     = False     , 
    is_json     = False     ,
    headers     = HEADERS   ,
    session     = None      ,
    cookies     = {}        ,
    timeout     = 10        ,
    proxies     = {}        ,
    verify      = False     ):
    '''Simple requests wrapper.

        A nice wrapper for the requests module.

        Args:
            url     (str                ): Request url.
            params  (dict               ): This can be either get, post or json data.
            is_post (bool               ): True if post request.
            is_json (bool               ): True if json request.
            headers (dict               ): Headers if needed.
            session (requests.Session   ): Requests session.
            cookies (dict               ): Cookies.

        Returns: 
            (requests.Response, requests.Session ): A response, session tuple.
    '''
    session = session if session else requests.Session()
    session.headers.update(HEADERS)
    session.proxies.update(proxies)
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    if      params and is_json  :
        sp  = session.post(
            url                 , 
            json    = params    , 
            verify  = verify    , 
            timeout = timeout   )
    elif    params and is_post  :
        sp  = session.post(
            url                 , 
            headers = headers   ,
            data    = params    , 
            verify  = verify    , 
            timeout = timeout   )
    elif    params              :
        sp  = session.get(
            url                         ,
            headers = headers           ,
            params  = urlencode(params) ,
            verify  = verify            ,
            timeout = timeout           )
    else                        :
        sp  = session.get(
            url                 ,
            headers = headers   ,
            verify  = False     ,
            timeout = timeout   )
    return sp, session
def g_xpath     (
    element , 
    xpath   ):
    '''Find by xpath

        Evaluate an xpath expression and returns the result
        
        Args:
            element (object ): Can be either a raw html/xml string or an lxml element.
            xpath   (str    ): xpath expression.

        Returns:
            (list, str  ): An array of strings
    '''
    #If the element has a method xpath
    if      hasattr(element, 'xpath')   :
        result  = element.xpath(xpath)
    elif    isinstance(element, str)    :
        try                                         :
            result  = fromstring(element).xpath(xpath)
        except    lxml.etree.XMLSyntaxError as e    :
            result  = fromstring(f'<html>{element}</html>').xpath(xpath)
    else                                :
        raise TypeError("Expected str or lxml.etree._Element.")
    return result