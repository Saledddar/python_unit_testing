from    datetime        import  datetime        as dt
from    collections     import  OrderedDict
from    enum            import  Enum
from    pprint          import  pformat

import  saltools.common as      sltc
import  pytest 

def test_DummyObj   (
    ):
    dobj    = sltc.DummyObj()

    assert  dobj()              is dobj
    assert  dobj.a()            is dobj
    assert  dobj.a().b.c.d()    is dobj
    assert  dobj.a(1,2,'x')     is dobj
def test_AutoObj    (
    ):
    class XClass(sltc.AutoObj):
        pass
    xclass  = XClass(
        1           , 
        2           ,
        3           ,
        a   = 'a'   , 
        b   = 'b'   )
    
    assert xclass.__dict__ == {
        'param_0'   : 1     ,
        'param_1'   : 2     ,
        'param_2'   : 3     ,
        'a'         : 'a'   ,
        'b'         : 'b'   }

class TestEasyObj   (
    ):
    def test_default_parsers    (
        self    ):
        parser  = sltc.EasyObj.DEFAULT_PARSERS[dt]
        assert  parser('1577689633.7279496') == parser('2019-12-30T08:07:13.727950')
    def test_params             (
        self    ):
        #Tests inheritance, default params, positional params, named params.
        class A(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('a0'   , {}            ),
                ('a1'   , {}            ),
                ('ax'   , {
                    'default'   : 'ax'  }),))
        class B(
            A   ):
            EasyObj_PARAMS  = OrderedDict((
                ('b0'   , {}            ),
                ('b1'   , {}            ),
                ('bx'   , {
                    'default'   : 'bx'  }),))
        class C(
            A   ):
            EasyObj_PARAMS  = OrderedDict((
                ('c0'   , {}            ),
                ('c1'   , {}            ),
                ('cx'   , {
                    'default'   : 'cx'  }),))
        class D(
            C   ,
            B   ):
            EasyObj_PARAMS  = OrderedDict((
                ('d0'   , {}            ),
                ('d1'   , {}            ),
                ('dx'   , {
                    'default'   : 'dx'  }),))
        a   = A('a0', 'a1')
        b   = B('a0', 'a1', 'b0', 'b1')
        c   = C('a0', 'a1', 'c0', 'c1')
        d   = D('a0', 'a1', 'b0', 'b1','c0', 'c1', 'd0', 'd1')
        d2  = D('a0', 'a1', 'b0', 'b1','c0', 'c1', 'd0', 'd1', cx= 'cx2', dx= 'dx2')
        assert  a.__dict__  ==  {
            'a0'    : 'a0'  ,
            'a1'    : 'a1'  ,
            'ax'    : 'ax'  }
        assert  b.__dict__  ==  {
            'a0'    : 'a0'  ,
            'a1'    : 'a1'  ,
            'b0'    : 'b0'  ,
            'b1'    : 'b1'  ,
            'bx'    : 'bx'  ,
            'ax'    : 'ax'  }
        assert  c.__dict__  ==  {
            'a0'    : 'a0'  ,
            'a1'    : 'a1'  ,
            'c0'    : 'c0'  ,
            'c1'    : 'c1'  ,
            'cx'    : 'cx'  ,
            'ax'    : 'ax'  }
        assert  d.__dict__  ==  {
            'a0'    : 'a0'  ,
            'a1'    : 'a1'  ,
            'b0'    : 'b0'  ,
            'b1'    : 'b1'  ,
            'c0'    : 'c0'  ,
            'c1'    : 'c1'  ,
            'd0'    : 'd0'  ,
            'd1'    : 'd1'  ,
            'ax'    : 'ax'  ,
            'bx'    : 'bx'  ,
            'cx'    : 'cx'  ,
            'dx'    : 'dx'  }
        assert  d2.__dict__ ==  {
            'a0'    : 'a0'  ,
            'a1'    : 'a1'  ,
            'b0'    : 'b0'  ,
            'b1'    : 'b1'  ,
            'c0'    : 'c0'  ,
            'c1'    : 'c1'  ,
            'd0'    : 'd0'  ,
            'd1'    : 'd1'  ,
            'ax'    : 'ax'  ,
            'bx'    : 'bx'  ,
            'cx'    : 'cx2' ,
            'dx'    : 'dx2' }
    def test_parsers            (
        self    ):
        class   A(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0'   , {
                    'parser'    : lambda x: int(x)+1, 
                    'type'      : int               }),
                ('p1'   , { 
                    'type'      : bool              }),))
        class   B(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0'   , {
                    'parser'    : lambda x: int(x)+1.0  , 
                    'type'      : int                   }),))
            
        a1  = A('1' , 'y'   )
        a2  = A(1   , False )
        assert a1.p0 == 2 and a1.p1 == True
        assert a2.p0 == 1 and a2.p1 == False
        
        with pytest.raises(AssertionError, match=r'.*Parser type .*'):
            b1  = B('1')
    def test_args_kwargs        (
        self    ):
        class TestEnum  (
            Enum    ):
            P0  = 0
            P1  = 1
            P2  = 2
        class A         (
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0'   , {
                    'type'      : str               ,
                    'parser'    : lambda x: x+ x    ,
                    'adapter'   : lambda x: x+ x    },),
                ('p1'   , {
                    'default'   : 'P0'      ,
                    'type'      : TestEnum  },),
                ('p2'   , {
                    'default'   : '1'       ,
                    'type'      : int       },),))
        class B         (
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0'   , {
                    'type'  : int   },),
                ('p1'   , {
                    'type'  : A     },),))

        a_args      = ['A']
        b_args      = [2, a_args]
        a_kwargs    = {
            'p0'    : 'AX'  ,
            'p1'    : 'P2'  ,
            'p2'    : '50'  }
        b_kwargs    = {
            'p0'    : '10'  , 
            'p1'    :a_args }

        aa  = A(*a_args)
        ba  = B(*b_args)
        ak  = A(**a_kwargs)
        bk  = B(**b_kwargs)

        assert  aa.__dict__ ==  {
            'p0'    : 'AA'          ,   #Only adapter is applied.
            'p1'    : TestEnum.P0   ,   #Correct Enum parsing from the default value.
            'p2'    : 1             }   #Corrent int parsing from the default value.
        assert  isinstance(ba.p1, A)
        assert  ba.p0 == 2
        assert  ak.__dict__ ==  {
            'p0'    : 'AXAX'        ,
            'p1'    : TestEnum.P2   ,
            'p2'    : 50            }
        assert  isinstance(bk.p1, A)
        assert  bk.p0 == 10
    def test_easy_obj_parser    (
        self    ):
        class A(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0'   , {}    ),
                ('p1'   , {}    ),
                ('p2'   , {}    ),))
            @classmethod
            def _EasyObj_parser (
                cls     ,
                *args   ,
                **kwargs):
                return args[0].split(), {}
        
        a   = A('p0 p1 p2')
        assert a.__dict__   == {
            'p0'    : 'p0'  ,
            'p1'    : 'p1'  ,
            'p2'    : 'p2'  }
    def test_generics           (
        self    ):
        class A(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('pA0'  , {}    ),))
        class B(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('pB0'  , {
                    'type'  : [A]   }),
                ('pB1'  , {
                    'type'  : [int] }),))
        a0  = A('pA0')
        b0  = B(a0, 1)
        b1  = B(['pA0', 'pA0'], [1])
        assert  b0.__dict__ == {
            'pB0'   : [a0]  ,
            'pB1'   : [1]   }
        assert  b0.pB0[0].pA0 == 'pA0'
    def test_str                (
        self    ):
        class A(
            sltc.EasyObj    ):
            EasyObj_PARAMS  = OrderedDict((
                ('p0', {}),))
        
        a           = A(None)
        b           = A('xxx')
        a.p0        = [a, b] 
        str_str     = a.__str__()
        rep_str     = a.__repr__()
        assert  'object_id' in str_str
        assert  'xxx'       in str_str
        