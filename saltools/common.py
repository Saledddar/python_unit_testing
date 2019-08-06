from    collections     import  OrderedDict
from    enum            import  Enum
from    inspect         import  getmro

class   InfoExceptionType(Enum):
    PROVIDED_TWICE  = 1
    MISSING         = 2
    EXTRA           = 3

class   ExceptionKwargs(Exception):
    '''
        Raised on kwargs setting errors by EasyObj.

        Args :
            kwargs (list): List of kwargs.
            error (InfoExceptionType): Error to print to the user
    '''

    def __init__(
        self        , 
        kwargs      ,
        error       ,
        all_kwargs  ):
        self.kwargs     = kwargs
        self.error      = error
        self.all_kwargs = '\nPossible kwargs:\n\t'+ '\n\t'.join(
            [ '{}{}'.format(x, (': '+ str(all_kwargs[x]['default']) if 'default' in all_kwargs[x] else ''))
                for x in all_kwargs])

    def __str__(self):
        return 'The following kwargs/args were {}: {}'.format(
            self.error.name.lower().replace('_',' ')    ,
            ', '.join(self.kwargs)                      )+ self.all_kwargs

    def __repr__(self):
        return str(self)

class   EasyObj():
    '''
        Allows automatic attribute setting from within __init__.
        All derived classes must call super with the provided kwargs 
            when implementing __init__ :
            super().__init__(**kwargs)
        EasyObj_KWARGS dict must be overridden.
        If args are supplied to init, they will be assigned automatically 
            using the order specified in EasyObj_KWARGS.
        Kwarg dict keys are the name of the kwargs, values are dict 
            containing a default value and an adapter, both are optional.
        If no value was given to a kwarg, default value is used, if no default value
            is found, ExceptionKwargs is raised.
        Adapters are applied to parameters even to default values.

        Support for kwargs inheritance:
            If a class B is derived from A and both A and B are EasyObj then 
                B.EasyObj_KWARGS will be A.EasyObj_KWARGS + B.EasyObj_KWARGS
            In this case, the EasyObj_KWARGS order will be dependent on the order of 
            types returned by inspect.getmro in reverse.

        Examples:
            >>> class A(EasyObj):
                    EasyObj_KWARGS  = OrderedDict((
                        ('name'     , {'default': 'Sal' , 'adapter': lambda x: 'My name is '+x  }),
                        ('age'      , {'default': 20    }                                        ),
                        ('degree'   , {}                                                         ),
                        ('degree'   , {'adapter': lambda x: x.strip()}                           )))
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)

            >>> #Class be doesn't have to implement __init__ since A already does that
            >>> class B(A):
                    EasyObj_KWARGS  = OrderedDict((
                        ('male' , {'default': True  }   ),))

            >>> A(degree= ' bachelor ').__dict__
            >>> {'degree': 'bachelor', 'name': 'My name is Sal', 'age': 20}
            >>> B(degree= ' bachelor ').__dict__
            >>> {'degree': 'bachelor', 'name': 'My name is Sal', 'age': 20, 'male': True}
    '''
    #Contains kwargs and validators for creating the object, must be overridden
    #Must be an ordered dict.
    EasyObj_KWARGS  = OrderedDict()
    
    def __init__(self, *args, **kwargs):
        all_kwargs = OrderedDict()
        for _type in reversed(getmro(type(self))):
            if hasattr(_type, 'EasyObj_KWARGS'):
                all_kwargs.update(_type.EasyObj_KWARGS)

        if len(args) > len(all_kwargs):
            extra_args = ['Arg at postition '+ str(i+1) for i in range(len(all_kwargs), len(args))]
            raise ExceptionKwargs(extra_args, InfoExceptionType.EXTRA, all_kwargs)

        args_kwargs     = {
            list(all_kwargs.keys())[i] : args[i] for i in range(len(args))}
        twice_kwargs    = [kwarg for kwarg in kwargs if kwarg in args_kwargs]

        if twice_kwargs:
            raise ExceptionKwargs(twice_kwargs, InfoExceptionType.PROVIDED_TWICE, all_kwargs)
        
        kwargs.update(args_kwargs)
        default_kwargs = {
            x:all_kwargs[x]['default'] for x in all_kwargs \
                if 'default' in all_kwargs[x] and x not in kwargs}
        kwargs.update(default_kwargs)

        extra_kwargs    = [k for k in kwargs if k not in all_kwargs] 
        if extra_kwargs     :
            raise ExceptionKwargs(extra_kwargs, InfoExceptionType.EXTRA, all_kwargs)

        missing_kwargs  = [k for k in all_kwargs if k not in kwargs] 
        if missing_kwargs   :
            raise ExceptionKwargs(missing_kwargs, InfoExceptionType.MISSING, all_kwargs)

        for k in kwargs :
            if 'adapter' in all_kwargs[k]:
                setattr(self, k, all_kwargs[k]['adapter'](kwargs[k]))
            else :
                setattr(self, k, kwargs[k])
