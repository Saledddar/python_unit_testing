'''Wen utilities.

    Web utilities.
'''
from    lxml.html       import  fromstring      , HtmlElement
from    .logging        import  handle_exception, Level
from    urllib.parse    import  urlencode

import  requests
import  lxml

requests.packages.urllib3.disable_warnings()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'} 

@handle_exception()
def do_request(
    url                     , 
    params      = None      , 
    is_post     = False     , 
    is_json     = False     ,
    headers     = HEADERS   ,
    session     = None      ,
    cookies     = {}        ):
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
            (requests.models.Response, requests.Session ): A response, session tuple.
    '''
    session = session if session else requests.Session()
    session.headers.update(HEADERS)
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])

    #a json request
    if params and is_json :
        r = session.post(url, json= params, verify= False)

    #A post request
    elif params and is_post:
        r = session.post(url, headers= headers,data = params, verify= False)

    #A get request with params
    elif params :
        r = session.get(url, headers =headers, params= urlencode(params), verify= False)

    #A simple get request
    else :
        r = session.get(url, headers =headers, verify =False)

    #Return the response
    return r, session

@handle_exception()
def find_xpath(element, xpath):
    '''Find by xpath

        Evaluate an xpath expression and returns the result
        
        Args:
            element (obj    ): Can be either a raw html/xml string or a n lxml element.
            xpath   (str    ): xpath expression.

        Returns:
            (list, str  ): An array of strings
    '''
    #If the element is a raw html text, create an lxml tree
    if type(element) is not HtmlElement :
        result = fromstring(element).xpath(xpath)
    #Else, evaluate the expression
    else :
        result = fromstring(lxml.etree.tostring(element)).xpath(xpath)
    return result