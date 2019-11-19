'''Common tools used by other modules.

    Basic low level features to be used buy other modules.

    Notes:
        EasyObj notes:

        * All derived classes must call super with the provided args/kwargs when overriding/overloading ``__init__`` as
            ``EasyObj.__init__(self, *args, **kwargs)`` in case of multiple base classes.
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
from    pprint          import  pformat

MY_CLASS    = '''
    Just something to indicate that the type of the parameter is the same
        as the declaring class since the type cannot be used before is declared.
    '''
 
class InfoExceptionType   (Enum):
    PROVIDED_TWICE  = 1
    MISSING         = 2
    EXTRA           = 3

class ExceptionKwargs     (Exception):
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
class ExceptionWrongType  (Exception):
    '''Raised by `EasyObj`.

        Raised when a type is specified for a parameter and is not matched on initiation.

        Args:
            param           (str    ): The name of the parameter.
            expected_type   (Type   ): The expected type.
            param_type      (Type   ): Provided type.
    '''
    def __init__(
        self            ,
        instanace_type  , 
        param           ,
        expected_type   ,
        param_type      ,
        value           ):
        self.instanace_type = instanace_type
        self.param          = param
        self.expected_type  = expected_type
        self.param_type     = param_type
        self.value          = value

    def __str__(self):
        return '{}, Wrong type for {}: expected {}, found {}, value {}.'.format(
            self.instanace_type ,
            self.param          , 
            self.expected_type  , 
            self.param_type     , 
            self.value          )

    def __repr__(self):
        return str(self)
 
class EasyObj   :
    '''Automatic attribute creation from params.

        Automatic attribute creation from params that supports default parameters, adapters,
        and inheritance.
        
    '''
    DEFAULT_PARSERS = {
        bool    : lambda x  :\
            True        if x.lower() in ['yes', 'y', 'true' , 'ok' , '1', 't']  \
            else False  if x.lower() in ['no' , 'n', 'false', 'not', '0', 'f']  \
            else exec('raise Exception()')                                      ,
        int     : int       ,
        float   : float     }
    #Contains params and validators for creating the object, must be overridden
    #Must be an ordered dict.
    EasyObj_PARAMS  = OrderedDict()

    @classmethod            
    def _EasyObj_parser     (
        cls     ,
        *args   ,
        **kwargs):
        return args, kwargs
    @classmethod
    def _g_all_values       (
        cls         ,
        obj         ,
        args        ,
        kwargs      ,
        def_params  ):
        '''Gets all params values.

            Checks and gets all params values including default params
        '''
        #Extra params check
        if len(args) > len(def_params):
            extra_params = [
                'Param at postition '+ str(i+1) for i in range(len(def_params), len(args))]
            raise ExceptionKwargs(obj, extra_params, InfoExceptionType.EXTRA, def_params)

        #Check for params appearing twice
        def_params_names= list(def_params.keys()) 
        params_args     = {
            list(def_params.keys())[i] : args[i] for i in range(len(args))}
        twice_params    = [
            kwarg for kwarg in kwargs if kwarg in params_args]
        if twice_params:
            raise ExceptionKwargs(obj, twice_params, InfoExceptionType.PROVIDED_TWICE, def_params)
        
        params  = kwargs
        params.update(params_args)

        default_params = {
            x:def_params[x]['default'] for x in def_params \
                if 'default' in def_params[x] and x not in params}
        params.update(default_params)

        extra_params    = [
            k for k in params if k not in def_params] 
        if  extra_params     :
            raise ExceptionKwargs(obj, extra_params, InfoExceptionType.EXTRA, def_params)

        missing_params  = [
            k for k in def_params if k not in params] 
        if  missing_params   :
            raise ExceptionKwargs(obj, missing_params, InfoExceptionType.MISSING, def_params)
        return  params
    @classmethod
    def _g_all_params       (
        cls ):
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
    def _g_recursive_params (
        cls         ,
        def_params  ):
        '''Gets parameters that implement `EasyObj`.

            Gets all __init__ paramaters that are derived from `EasyObj`

            Returns:
                dict    : parameter name, parameter type object.
        '''
        recursive_params    = {}
        for param in def_params :
            def_type = def_params[param].get('type')
            if      isinstance(def_type, list)      :
                def_type    = def_type[0]
            if      not def_type                    :
                continue
            elif    def_type   == MY_CLASS          :
                recursive_params[param] = cls
            elif    issubclass(def_type, EasyObj)   :
                recursive_params[param] = def_type
        
        return recursive_params 
    @classmethod
    def _g_param_value      (
        cls                     ,
        param                   ,
        value                   ,
        def_params              ,
        recursive_params        ,
        def_type        = None  ):
        '''Gets the value of a given parameter

            The value is returned respecting the following constraints in order:
                - If None, set to None.
                - If no type is specified, set to value.
                - If the type is a list                 :
                    - If value is a list    :
                        - recursion on each element with the generic type.
                    - If value is not a list    :
                        - recursion on value  with the generic type.
                - If value is an instance of the type   :
                    - Set to value.
                - If type is Enum and values is a string:
                    - Try parsing.
                - If type is an Easy_Obj and not set    :
                - If a parser exists                    :
                    - Set to parser return value.
                    - Pass args or kwargs.
                - If all the above failed, raise an exception.
                - Apply the adapter if any.

        '''
        if      def_type    == None :
            def_type            = def_params[param].get('type')
        parser              = def_params[param].get(
            'parser'                , 
            cls.DEFAULT_PARSERS.get (
                def_type            ) if isinstance(def_type, type) else None)
        adapter             = def_params[param].get('adapter')
        param_value         = value
        if      def_type    == MY_CLASS :
            def_type    = cls

        if      value       == None                     :
            param_value = value
        elif    def_type    == None                     :
            param_value = value
        elif    isinstance(def_type , list      )       :
            if      isinstance(value, list) :
                param_value = [
                    cls._g_param_value(
                        param           , 
                        x               , 
                        def_params      , 
                        recursive_params,
                        def_type[0]     ) for x in value]
            else                            :
                param_value = [
                    cls._g_param_value(
                        param           , 
                        value           , 
                        def_params      , 
                        recursive_params,
                        def_type[0]     )]
        elif    isinstance(value    , def_type  )       :
            param_value = value 
        elif    issubclass(def_type , Enum      )   and \
                isinstance(value    , str       )       :
            param_value = getattr(def_type, value)       
        elif    param in recursive_params               :
            if      isinstance(value    , dict      )   :
                param_value = def_type(**value)
            elif    isinstance(value    , list      )   :
                param_value = def_type(*value)
            else                                        :
                param_value = def_type(value)
        elif    parser      != None                     :
            param_value = parser(value)
            assert  isinstance(param_value, def_type),\
                f'Parser type {type(param_value)} is not {def_type} : {param} = {value}'
        else                                            :
            raise ExceptionWrongType(
                        cls         ,
                        param       ,
                        def_type    ,
                        type(value) ,
                        value       )
        
        return adapter(param_value) if adapter else param_value
    
    def __init__    (
        self    , 
        *args   , 
        **kwargs):
        my_type             = type(self)
        args, kwargs        = my_type._EasyObj_parser(*args, **kwargs)
        #Get all inherited params
        def_params          = my_type._g_all_params()
        #Checks values params 
        params              = my_type._g_all_values(self, args, kwargs, def_params)
        #Get EasyObj params
        recursive_params    = my_type._g_recursive_params(def_params)
        #Try custom parsing logic


        for param in params :
            setattr(
                self                    , 
                param                   , 
                my_type._g_param_value  (
                    param           , 
                    params[param]   , 
                    def_params      , 
                    recursive_params)   )
        
        for base in list(reversed(getmro(my_type)))[:-1]    :
            if      hasattr(base, '_on_init')   :
                    base._on_init(self)
        self._on_init()
    def __str__     (
        self        ,
        exclude = []):
        dict_   = {
            'object_id' : id(self)  }
        exclude.append(self)
        for k,v in self._g_all_params().items():
            obj         = getattr(self, k)
            is_easy_obj = hasattr(type(obj), 'EasyObj_PARAMS')
            if      not is_easy_obj :
                dict_[k]    = obj
            else                    :
                if      obj not in exclude  :
                    dict_[k]    = obj.__str__(exclude)
                else                        :
                    dict_[k]    = id(obj)
        return pformat(dict_) 
                
    def _on_init(
        self    ):
        '''Executed after `__init___`.

        '''
        pass
class AutoObj   :
    def __init__(
        self        ,
        *args       ,
        **kwargs    ):
        for i in range(len(args))   :
            setattr(self, f'param_{i}', args[i])
        for k,v in kwargs.items()   :
            setattr(self, k, v)
class DummyObj  (
    EasyObj ):
    '''An object that never returns None.

        Can be used instead of checking for None before calling a method or an attribute

        Example:
            >>> class A():
            >>>     def f(self):
            >>>         print('A.f()')
            >>> a = A()
            >>> a.f()
                A.f()
            >>> #DummyObj can be used to fill in a variable that might be null
            >>> a = DummyObj()
            >>> a.f().b
                <saltools.common.DummyObj at 0x____>
            >>> #The above can be written otherwise as:
            >>> if      a != None   :
            >>>     if      a.f() != None    : 
            >>>         a.f().b
            >>> #Supports function parameters
            >>> a.f().b.c(1,2).d.e()
                <saltools.common.DummyObj at 0x____>
    '''
    
    def __call__    (
        self        ,
        *args       ,
        **kwargs    ):
        return self
    def __getattr__ (
        self    , 
        name    ):
        return self