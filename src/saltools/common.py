'''Common tools used by other modules.

    Basic low level features to be used buy other modules.

    Notes:
        EasyObj notes:

        * All derived classes must call super with the provided args/kwargs when implementing ``__init__``.
          ``super().__init__(*args, **kwargs)`` or ``EasyObj.__init__(self, *args, **kwargs)`` in case of multiple
          base classes.
        * EasyObj_PARAMS dict must be overridden.
        * If args are supplied to ``__init__``, they will be assigned automatically 
          using the order specified in ``EasyObj_PARAMS``.
        * ``EasyObj_PARAMS`` dict keys are the name of the params, values are dict containing a default 
          value and an adapter, both are optional, if not default value is given to a param, it is considered
          a positional param.
        * If no value was given to a kwarg, the default value is used, if no default 
          value was specified, ExceptionKwargs is raised.
        * Adapters are applied to params after setting the default values.
        * Support for params inheritance:

          If a class ``B`` is derived from ``A`` and both ``A`` and ``B`` are ``EasyObj`` then:
          
          * ``B.EasyObj_PARAMS`` will be ``A.EasyObj_PARAMS.update(B.EasyObj_PARAMS)``.
          * The ``EasyObj_PARAMS`` order will be dependent on the order of 
            types returned by ``inspect.getmro`` reversed.
          * All params from all classes with no default value are considered positional, they must 
            be supplies to ``__init__`` following the order of classes return by 
            ``inspect.getmro`` then their order in ``EasyObj_PARAMS``.


    Example:
            Example for EasyObj:

            >>> #Let's define out first class A:
            >>> from saltools.common import EasyObj
            >>> class A(EasyObj):
            >>>     EasyObj_PARAMS  = OrderedDict((
            >>>         ('name'     , {'default': 'Sal' , 'adapter': lambda x: 'My name is '+x  }),
            >>>         ('age'      , {'default': 20    }                                        ),
            >>>         ('degree'   , {}                                                         ),
            >>>         ('degree'   , {'adapter': lambda x: x.strip()}                           )))
            >>>     def __init__(self, *args, **kwargs):
            >>>         super().__init__(*args, **kwargs)
            >>> #Class B doesn't have to implement __init__ since A already does that:
            >>> class B(A):
            >>>     EasyObj_PARAMS  = OrderedDict((
            >>>         ('id'   , {}                    ),
            >>>         ('male' , {'default': True  }   ),))
            >>> #Testing out the logic:
            >>> A(degree= ' bachelor ').__dict__
                {'degree': 'bachelor', 'name': 'My name is Sal', 'age': 20}
            >>> B(degree= ' bachelor ').__dict__
                {'degree': 'bachelor', 'id': ' id-001 ', 'name': 'My name is Sal', 'age': 20, 'male': True}
'''
from    collections     import  OrderedDict
from    enum            import  Enum
from    inspect         import  getmro

MY_CLASS    = '''
    Just something to indicate that the type of the parameter is the same
        as the declaring class since the type cannot be used before is declared.
    '''

class   InfoExceptionType   (Enum):
    PROVIDED_TWICE  = 1
    MISSING         = 2
    EXTRA           = 3
class   ExceptionKwargs     (Exception):
    '''Raised by EasyObj

        Raised by EasyObj when the params supplied to ``__init__`` do not 
        match the excpected defintion.

        Args:
            object      (EasyObject         ): The object that raised the exception.
            params      (list               ): The list of params casing the issue.
            error       (InfoExceptionType  ): The type of the error.
            all_params  (dict               ): The expected params.
    '''
    def __init__(
        self        , 
        object      ,
        params      ,
        error       ,
        all_params  ):
        self.object     = object
        self.params     = params
        self.error      = error
        self.all_params = '\nPossible params:\n\t'+ '\n\t'.join(
            [ '{}{}'.format(x, (': '+ str(all_params[x]['default']) if 'default' in all_params[x] else ''))
                for x in all_params])

    def __str__(self):
        return '{}, The following params were {}: {}'.format(
            self.object.__class__                       ,
            self.error.name.lower().replace('_',' ')    ,
            ', '.join(self.params)                      )+ self.all_params

    def __repr__(self):
        return str(self)
class   ExceptionWrongType  (Exception):
    '''Raised by `EasyObj`.

        Raised when a type is specified for a parameter and is not matched on initiation.

        Args:
            param           (str    ): The name of the parameter.
            expected_type   (Type   ): The expected type.
            param_type      (Type   ): Provided type.
    '''
    def __init__(
        self            , 
        param           ,
        expected_type   ,
        param_type      ):
        self.param          = param
        self.expected_type  = expected_type
        self.param_type     = param_type

    def __str__(self):
        return 'Wrong type for {}: expected {}, found {}.'.format(
            self.param, self.expected_type, self.param_type)

    def __repr__(self):
        return str(self)


class   EasyObj():
    '''Automatic attribute creation from params.

        Automatic attribute creation from params that supports default parameters, adapters,
        and inheritance.
        
    '''
    
    #Contains params and validators for creating the object, must be overridden
    #Must be an ordered dict.
    EasyObj_PARAMS  = OrderedDict()
    
    @classmethod
    def _g_all_params(cls):
        def_params                  = OrderedDict()
        def_positional_params       = OrderedDict()
        def_non_positional_params   = OrderedDict()

        #Get the full list of params from all the parent classes
        for _type in reversed(getmro(cls)):
            if hasattr(_type, 'EasyObj_PARAMS'):
                #Set positional params
                def_positional_params.update({
                    x: _type.EasyObj_PARAMS[x] for x in _type.EasyObj_PARAMS if\
                       'default' not in _type.EasyObj_PARAMS[x]} )
                #Set non positional params
                def_non_positional_params.update({
                    x: _type.EasyObj_PARAMS[x] for x in _type.EasyObj_PARAMS if\
                       'default' in _type.EasyObj_PARAMS[x]} )

        #Merge the params
        def_params = def_positional_params
        def_params.update(def_non_positional_params)

        return def_params

    @classmethod
    def _g_recursive_params(cls):
        '''Gets parameters that implement `EasyObj`.

            Gets all __init__ paramaters that are derived from `EasyObj`

            Returns:
                dict    : parameter name, parameter type object.
        '''
        recursive_params    = {}
        all_params          = cls._g_all_params()

        for param all_params :
            param_type = all_params.get('type')
            if      param_type and param_type   == MY_CLASS:
                recursive_params[param] = cls
            elif    param_type and issubclass(param_type, EasyObj):
                recursive_params[param] = param_type
        
        return recursive_params
            
    @classmethod
    def g_from_dict(cls, params):
        '''Gets an object instance from a python `dict`.

            Creates an instance from a dict of params, nested dicts can be used to instantiate 
            parameters that are derived from EasyObj:

            Args:
                params  : Object parameteres as dict.
            Returns:
                EasyObj : An instance of the type.
        '''
        assert isinstance(params, dict), 'An instance of EasyObject must only be created from a dict.'

        recursive_params    = cls._g_recursive_params()
        kwargs              = {}
        all_params          = cls._g_all_params()
        for param in params :
            if      cls.all_params[param].get('parser') and isinstance(params[param], str)  :
                params[param]   = all_params[param].get('parser')(params[param])
            
            param_type      = all_params[param].get('type')     
            if      not param_type:
                kwargs[param]   = params[param]
                continue
            if      param in  recursive_params:
                param_type  = recursive_params[param]
                if      isinstance(params[param], list):
                    kwargs[param]   = [param_type.g_from_dict(y)            \
                        if  not isinstance(y, param_type) else y for y in params[param]]
                else    :
                    kwargs[param]   = param_type.g_from_dict(params[param]) \
                        if not isinstance(params[param], param_type) else params[param]
            elif    issubclass(param_type, Enum) and isinstance(params[param], str):
                    kwargs[param]   = getattr(param_type, params[param])
                
        return cls(** kwargs)

    def __init__(self, *args, **kwargs):
        #Get all inherited params
        def_params = type(self)._g_all_params()
        
        #Extra params check
        if len(args) > len(def_params):
            extra_params = ['Param at postition '+ str(i+1) for i in range(len(def_params), len(args))]
            raise ExceptionKwargs(self, extra_params, InfoExceptionType.EXTRA, def_params)

        #Check for params appearing twice
        params_args     = {
            list(def_params.keys())[i] : args[i] for i in range(len(args))}
        twice_params    = [kwarg for kwarg in kwargs if kwarg in params_args]
        if twice_params:
            raise ExceptionKwargs(self, twice_params, InfoExceptionType.PROVIDED_TWICE, def_params)
        
        params  = kwargs
        params.update(params_args)

        default_params = {
            x:def_params[x]['default'] for x in def_params \
                if 'default' in def_params[x] and x not in params}
        params.update(default_params)

        extra_params    = [k for k in params if k not in def_params] 
        if  extra_params     :
            raise ExceptionKwargs(self, extra_params, InfoExceptionType.EXTRA, def_params)

        missing_params  = [k for k in def_params if k not in params] 
        if  missing_params   :
            raise ExceptionKwargs(self, missing_params, InfoExceptionType.MISSING, def_params)

        for param in params :
            if  'adapter' in def_params[param]:
                value = def_params[param]['adapter'](params[param])
            else :
                value = params[param]
            
            param_type  = def_params[param].get('type')
            if  param_type:
                #Check if list and all elements are of the correct type
                if      isinstance(value, list):
                    for i in range(len(value)):
                        if      not issubclass(type(value[i]), param_type) :
                            raise ExceptionWrongType(
                            '{} postion {}'.format(param, i)    ,
                            param_type                          ,
                            type(value[i])                      )
                elif    not issubclass(type(value), param_type) :
                    raise ExceptionWrongType(
                        param       ,
                        param_type  ,
                        type(value) )
                
            setattr(self, param, value)

    def __str__(self, inline= True):
        '''Gets an str for the attributes.

            A string representation for the object attributes.\
            
            Args:
                inline  (bool   ): If true, returns a one line string, else a multiline string.

            Returns:
                str : An str with the attributes and their values
        '''
        return (', ' if inline else '\n').join(['{}: {}'.format(x, getattr(self, x)) for x in self.EasyObj_PARAMS])
    
    def __repr__(self):
        return str(self)