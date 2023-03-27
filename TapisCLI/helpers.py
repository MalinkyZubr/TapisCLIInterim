import typing
import sys
import threading
from TypeEnforcement.type_enforcer import TypeEnforcer
try:
    from . import decorators
except:
    import decorators


def get_parameters(func):
    return func.__code__.co_varnames[:func.__code__.co_argcount]

class OperationsHelper:
    decorators_list = [decorators.RequiresForm, decorators.Auth, decorators.NeedsConfirmation, decorators.RequiresExpression]
    def filter_kwargs(self, func: typing.Callable, kwargs: dict) -> dict:
        filtered = dict()
        variables = list(get_parameters(func))
        variables.remove('self')
        for arg in variables:
            print(arg)
            print(kwargs[arg])
            filtered.update({arg:kwargs[arg]})
        return filtered

    def configure_decorators(self):
        for decorator in OperationsHelper.decorators_list:
            decorator.connection = self.connection
            decorator.username = self.username
            decorator.password = self.password


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
    