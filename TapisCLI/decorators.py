try:
    from . import helpers
    from . import schemas
    from . import SocketOpts
    from . import exceptions
except:
    import helpers
    import schemas
    import SocketOpts
    import exceptions

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
        if not fields:
            raise AttributeError(f"The decorated function {self.function} has no parameters.")
        form_request = schemas.FormRequest(arguments_list=fields)
        self.json_send(form_request.dict())
        filled_form: schemas.FormResponse = self.schema_unpack().arguments_list

        return self.function(**filled_form)


class RequiresExpression(BaseRequirementDecorator):
    def __call__(self, *args, **kwargs):
        fields = list(helpers.get_parameters(self.function))
        if 'expression' not in fields:
            raise AttributeError(f"The function {self.function} does not contain an 'expression' parameter")
        form_request = schemas.FormRequest(arguments_list=[])
        self.json_send(form_request.dict())
        filled_form: schemas.FormResponse = self.schema_unpack()
        kwargs['expression'] = filled_form.arguments_list

        return self.function(**kwargs)
    

class Auth(BaseRequirementDecorator):
    def __call__(self, *args, **kwargs):
        fields = list(helpers.get_parameters(self.function))
        if 'username' not in fields:
            raise AttributeError(f"The function {self.function} does not contain a 'username' parameter")
        elif 'password' not in fields:
            raise AttributeError(f"The function {self.function} does not contain a 'password' parameter")
        auth_request = schemas.AuthRequest()
        self.json_send(auth_request.dict())
        auth_data: schemas.AuthData = self.schema_unpack()
        kwargs['username'], kwargs['password'] = auth_data.username, auth_data.password

        return self.function(**kwargs)


class NeedsConfirmation(BaseRequirementDecorator):
    def __call__(self, *args, **kwargs):
        confirmation_request = schemas.ConfirmationRequest(message=f"You requested to {self.function.__name__}. Please confirm (y/n)")
        self.json_send(confirmation_request.dict())
        confirmation_reply: schemas.ResponseData = self.schema_unpack()
        confirmed = confirmation_reply.response_message
        if not confirmed:
            raise exceptions.NoConfirmationError(self.function)
        return self.function(**kwargs)



if __name__ == "__main__":
    @RequiresForm(connection='yabadabadoo')
    def silly(doof):
        pass
