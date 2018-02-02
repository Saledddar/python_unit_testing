from pyunet import unit_test

#Set this to true
unit_test.DO_TESTS = True

#Simple use case
@unit_test(
    [
        [
        #First test case
        [4,5]       ,       #Args
        {}          ,       #Kwargs
        9           ,       #Assertion
        ],
        [
        #Second test case, using kwargs
        [3]         ,       #Args
        {'y' : 3}   ,       #Kwargs
        6           ,       #Assertion
        ]
    ]
    )
def add(x,y):
    return x+y

#This will not be tested
@unit_test(
    [
        [
        #First test case
        [4,5]   ,       #Args
        {}      ,       #Kwargs
        20      ,       #Assertion
        ],
        [
        #Second test case
        [3,3]   ,       #Args
        {}      ,       #Kwargs
        9       ,       #Assertion
        ]
    ],
    skip = True
    )
def mul(x,y):
    return x*y

#lambda assertion
@unit_test(
    [
        [
        ['aba','b','d'] ,
        {}              ,
        lambda x : 'b' not in x and 'd' in x    ,       #Assertion using a lambda expression
        ]
    ]
    )
def replace(original_text,text_to_replace,replacement):
    return original_text.replace(text_to_replace,replacement)

#As a method
class JustAClass():
    #lambda assertion
    @unit_test(
        [
            [
            []              ,
            {}              ,
            'JustAClass'    ,
            ]
        ]
        )
    def my_name(self):
        return self.__class__.__name__
