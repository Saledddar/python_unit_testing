"""
Entry point of the package
"""
import argparse

#Set the arg parser
parser = argparse.ArgumentParser(description='A collection of tools',prog='python -m saltools')
parser.add_argument('name'  ,metavar='N'    ,default = ''            ,   help='The name of the package'                      )
