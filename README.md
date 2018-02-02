# Pyunet
A unit testing tool for python

Description
--
This is a light weight unit testing tool that makes it easier to write your unit tests for python using decorators or wrappers.

Capabilities:
--
- an easy way to write unit tests using decorators :

```
from pyunet import unit_test

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


Usage
--
Demo.py illustates the usage
