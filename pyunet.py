"""
Unit tests made easy
"""
import inspect
import types

#Contains the list of already tested methods
TESTED_FUNCTIONS    = []
#Set to false to skip all testing
DO_TESTS            = True

def unit_test(_args=[],skip = False):
    """
    Perform a unit test on the decorated method or function
    Args    :
        _args   : The arguments for the unit test decorator are a list of list of three elements: args,kwargs, and assertion.
            If the function is a method, it must have the first argument named as self.
        skip    : If set to True, the unit test is skipped
    """
    def _unit_test(fn):
        def wrapper_unit_test(*args, **kwargs):
            #Checks if the function is a mehtod and should have the self argumetn passed
            try :
                is_method   = inspect.getargspec(fn)[0][0] == 'self'
            except :
                is_method   = False

            #Builds the name of the method,module.class.method or module.method
            if is_method :
                name    = '{}.{}.{}'.format(fn.__module__, args[0].__class__.__name__, fn.__name__)
            else :
                name    = '{}.{}'.format(fn.__module__, fn.__name__)

            #If the method had been tested already
            if name in TESTED_FUNCTIONS or not DO_TESTS or skip :
                if skip :
                    print ('Skipped : {}'.format(name))
                return  fn(*args,**kwargs)

            #Run throught the tests one by
            for _test in _args :
                #Pass the self arg if the function is a method
                if is_method :
                    result = fn(*([args[0]]+_test[0]),**_test[1])
                else :
                    result = fn(*_test[0],**_test[1])

                #If the expression to verify against is a function or a lambda expression
                if type(_test[2]) == types.FunctionType :
                    assert _test[2](result),'{} : Case {}'.format(name,_args.index(_test)+1)
                else :
                    assert  result == _test[2],'{} : Case {}'.format(name,_args.index(_test)+1)
            print ('Tested : {}'.format(name))
            TESTED_FUNCTIONS.append(name)
            return  fn(*args,**kwargs)
        return wrapper_unit_test
    return _unit_test
