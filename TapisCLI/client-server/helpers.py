import typing
from TypeEnforcement.type_enforcer import TypeEnforcer


class OperationsHelper:
    #@TypeEnforcer.enforcer(recursive=True)
    def filter_kwargs(self, func: typing.Callable, kwargs: dict) -> dict:
        filtered = dict()
        variables = list(func.__code__.co_varnames)
        variables.remove('self')
        for arg in variables:
            filtered.update({arg:kwargs[arg]})
        return filtered


if __name__ == "__main__":
    class Silly:
        def z(self, y=True, x=False):
            return None
    x = OperationsHelper()
    v=Silly()
    x.filter_kwargs(v.z, {'y':False, 'x':"True", 'z':"hi"})
    