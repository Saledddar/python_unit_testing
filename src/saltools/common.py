'''Common tools used by other modules

    Basic low level features to be used buy other modules.

    Notes:
        EasyObj notes:

        * All derived classes must call super with the provided args/kwargs when implementing ``__init__``.
          ``super().__init__(**args, **kwargs)``
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
            * ``B.EasyObj_PARAMS`` will be ``A.EasyObj_PARAMS.update(B.EasyObj_PARAMS)``
            * The ``EasyObj_PARAMS`` order will be dependent on the order of 
              types returned by ``inspect.getmro`` reversed.
            * All params from all classes with no default value are considered positional, they must 
              be supplies to ``__init__`` following the order of classes return by ``inspect.getmro`` 
              then their order in ``EasyObj_PARAMS``.


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

class   InfoExceptionType(Enum):
    PROVIDED_TWICE  = 1
    MISSING         = 2
    EXTRA           = 3

class   ExceptionKwargs(Exception):
    '''Raised by EasyObj

        Raised by EasyObj when the params supplied to ``__init__`` do not 
        match the excpected defintion.

        Args:
            params      (list               ): The list of params casing the issue.
            error       (InfoExceptionType  ): The type of the error.
            all_params  (dict               ): The expected params.
    '''
    def __init__(
        self        , 
        params      ,
        error       ,
        all_params  ):
        self.params     = params
        self.error      = error
        self.all_params = '\nPossible params:\n\t'+ '\n\t'.join(
            [ '{}{}'.format(x, (': '+ str(all_params[x]['default']) if 'default' in all_params[x] else ''))
                for x in all_params])

    def __str__(self):
        return 'The following params were {}: {}'.format(
            self.error.name.lower().replace('_',' ')    ,
            ', '.join(self.params)                      )+ self.all_params

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
    
    def __init__(self, *args, **kwargs):
        def_params                  = OrderedDict()
        def_positional_params       = OrderedDict()
        def_non_positional_params   = OrderedDict()

        #Get the full list of params from all the parent classes
        for _type in reversed(getmro(type(self))):
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
        

        #Extra params check
        if len(args) > len(def_params):
            extra_params = ['Param at postition '+ str(i+1) for i in range(len(def_params), len(args))]
            raise ExceptionKwargs(extra_params, InfoExceptionType.EXTRA, def_params)

        #Check for params appearing twice
        params_args     = {
            list(def_params.keys())[i] : args[i] for i in range(len(args))}
        twice_params    = [kwarg for kwarg in kwargs if kwarg in params_args]
        if twice_params:
            raise ExceptionKwargs(twice_params, InfoExceptionType.PROVIDED_TWICE, def_params)
        
        params  = kwargs
        params.update(params_args)

        default_params = {
            x:def_params[x]['default'] for x in def_params \
                if 'default' in def_params[x] and x not in params}
        params.update(default_params)

        extra_params    = [k for k in params if k not in def_params] 
        if extra_params     :
            raise ExceptionKwargs(extra_params, InfoExceptionType.EXTRA, def_params)

        missing_params  = [k for k in def_params if k not in params] 
        if missing_params   :
            raise ExceptionKwargs(missing_params, InfoExceptionType.MISSING, def_params)

        for param in params :
            if 'adapter' in def_params[param]:
                setattr(self, param, def_params[param]['adapter'](params[param]))
            else :
                setattr(self, param, params[param])
