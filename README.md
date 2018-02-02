# Pyunet
A unit testing tool for python

Description
--
This is a light weight unit testing tool that makes it easier to write your unit tests for python using decorators.

Capabilities:
--
- An easy way to write unit tests using decorators, unit tests are performed before the first call to a function if **DO_TESTS** and **skip** are set to **True** and **False** respectively, first we need to put the script file **pyunet.py** in the same folder as the current module, and make an import statement :
```
from pyunet import unit_test
```

 We can then use **unit_test** :
 ```
@unit_test(
  [       #Cases list
      [   #Case 1
        [],                   #Args
        {},                   #Kwargs
        'This is what I do',  #Assertion
      ]
  ]
  )
def test_me():
    return 'This is what I do'
```

- Multiple test cases :
 ```
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
```

- Ability to use lambda expression to test the result of the test, this is useful in many cases :
 ```
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
```

- Can be used for methods, in this case the first argument must be named **self** :
 ```
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
```

- Clear output:
 - Failure:
 ```
 #As a method
 class JustAClass():
     #Failure!
     @unit_test(
         [
             [
             []              ,
             {}              ,
             'Worng answer!'    ,
             ]
         ]
         )
     def i_will_fail(self):
         return 'Correct answer'
```
   Ouput **AssertionError: demo.JustAClass.i_will_fail : Case 1** :
   ```
   >>> d.JustAClass().i_will_fail()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "pyunet.py", line 45, in wrapper_unit_test
    assert  result == _test[2],'{} : Case {}'.format(name,_args.index(_test)+1)
AssertionError: demo.JustAClass.i_will_fail : Case 1
```
 - Skip :
  ```
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
     ```
  Output :
  ```
  >>> d.mul(5,5)
Skipped : demo.mul
25
```
 - Success :
  ```
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
     ```
  Output :
  ```
  >>> d.add(1,2)
Tested : demo.add
3
```
