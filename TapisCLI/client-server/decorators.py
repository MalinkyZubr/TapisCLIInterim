try:
    from . import helpers
    from . import schemas
    from . import SocketOpts
except:
    import helpers
    import schemas
    import SocketOpts

import typing


class BaseRequirementDecorator(SocketOpts.SocketOpts, helpers.OperationsHelper):
    connection = None
    def __init__(self, func):
        self.function = func
        self.__code__ = func.__code__
        self.connection = BaseRequirementDecorator.connection

    def __repr__(self):
        return self.function
    
    def __str__(self):
        return str(self.function)


class RequiresForm(BaseRequirementDecorator):
    def __call__(self, *args, **kwargs):
        fields = list(helpers.get_parameters(self.function))
        form_request = schemas.FormRequest(arguments_list=fields)
        self.json_send(form_request.dict())
        filled_form = self.schema_unpack()
        return self.function(**filled_form)


class RequiresPassword(BaseRequirementDecorator):
    def __call__(self, *args, **kwargs):
        
        return self.function(*args, **kwargs)

if __name__ == "__main__":
    @RequiresForm(connection='yabadabadoo')
    def silly(doof):
        pass
