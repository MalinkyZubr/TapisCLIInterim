import typing
import sys
import threading
from TypeEnforcement.type_enforcer import TypeEnforcer
import re
import json
import argparse
try:
    from . import exceptions
except:
    import exceptions


def get_parameters(func):
    args = func.__code__.co_varnames[:func.__code__.co_argcount]
    if 'self' in args:
        args = args[1:]
    return args

class OperationsHelper:
    def filter_kwargs(self, func: typing.Callable, kwargs: dict) -> dict:
        filtered = dict()
        variables = list(get_parameters(func))
        variables.remove('self')
        for arg in variables:
            filtered.update({arg:kwargs[arg]})
        return filtered
    

class DynamicHelpUtility:
    """
    dynamically generate the help menu based on the docstring and function arguments using .__doc__ and .__code__
    to generate helps for each command, iterate over the command map of the selected tapis wrapper object, and generate separate help menu for each
    """
    def __locate_docstring_help(self, func: typing.Callable) -> str:
        docstring_components = func.__doc__.split("@")
        for docstring_component in docstring_components:
            if re.match(r'^[^:]+', docstring_component):
                return docstring_component.split("help: ")[1]
        else:
            raise exceptions.HelpDoesNotExist(func.__name__)
            
    def help_generation(self):
        help_menu = dict()
        for command_name, command in self.command_map.items():
            command_help = dict()
            command_help['command_name'] = command_name
            command_help['description'] = self.__locate_docstring_help(command)
            arguments = get_parameters(command)
            argument_help = f"{self.__name__}"
            for argument in arguments:
                argument_help += 

class KillableThread(threading.Thread):
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run     
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


if __name__ == "__main__":
    class Silly:
        def z(self, y=True, x=False):
            return None
    x = OperationsHelper()
    v=Silly()
    x.filter_kwargs(v.z, {'y':False, 'x':"True", 'z':"hi"})
    