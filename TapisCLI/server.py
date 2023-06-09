import pyfiglet
import argparse
import sys
from getpass import getpass
import time
import re
from tapipy.tapis import Tapis
import tapipy.tapis
import socket
import json
import threading
import multiprocessing
import os
import logging
from tapisObjectWrappers import Files, Apps, Pods, Systems, Neo4jCLI
from TypeEnforcement.type_enforcer import TypeEnforcer
import typing

try:
    from . import exceptions
    from . import SocketOpts as SO
    from . import helpers
    from . import schemas
    from . import decorators
except:
    import exceptions
    import SocketOpts as SO
    import helpers
    import schemas
    import decorators

class Server(SO.SocketOpts, helpers.OperationsHelper, decorators.DecoratorSetup, helpers.DynamicHelpUtility):
    @TypeEnforcer.enforcer(recursive=True)
    def __init__(self, IP: str, PORT: int):
        # logger setup
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler(stream=sys.stdout)

        file_handler = logging.FileHandler(
            r'logs.log', mode='w')
        stream_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.INFO)

        # set formats
        stream_format = logging.Formatter(
            '%(name)s - %(levelname)s - %(message)s')
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        stream_handler.setFormatter(stream_format)
        file_handler.setFormatter(file_format)

        # add the handlers
        self.logger.addHandler(stream_handler)
        self.logger.addHandler(file_handler)

        self.logger.disabled = False

        # setting up socket server
        self.ip, self.port = IP, PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)
        self.connection = None  # initialize the connection variable
        self.end_time = time.time() + 300  # start the countdown on the timeout

        self.logger.info("Awaiting connection")

        self.pods = None
        self.systems = None
        self.files = None
        self.apps = None
        self.neo4j = None
        self.t = None
        self.url = None
        self.access_token = None
        self.username = None
        self.password = None

        self.accept(initial=True)  # connection returns the tapis object and user info

        # instantiate the subsystems
        self.logger.info('initialization complete')
        self.command_group_map = {
            'pods':self.pods,
            'systems':self.systems,
            'files':self.files,
            'apps':self.apps
        }
        self.command_map = {
            'help':self.help,
            'whoami':self.pods.whoami,
            'exit':self.__exit,
            'shutdown':self.__shutdown,
            'switch_service':self.tapis_init
        }
        help0, help1 = self.help_generation()
        self.help = dict(help0, **help1)

    @decorators.Auth
    def tapis_init(self, username: str, password: str, name: str) -> tuple[typing.Any, str, str] | None:  # name is the baseURL
        """
        @help: switch the connected tapis service
        """
        start = time.time()
        self.username = username
        self.password = password
        t = Tapis(base_url=name,
                  username=username,
                  password=password)
        t.get_tokens()

        self.configure_decorators()
        # V3 Headers
        header_dat = {"X-Tapis-token": t.access_token.access_token,
                      "Content-Type": "application/json"}

        # Service URL
        url = f"{name}/v3"

        # create authenticator for tapis systems
        authenticator = t.access_token
        # extract the access token from the authenticator
        access_token = re.findall(
            r'(?<=access_token: )(.*)', str(authenticator))[0]

        self.pods = Pods(t, username, password, self.connection)
        self.systems = Systems(t, username, password, self.connection)
        self.files = Files(t, username, password, self.connection)
        self.apps = Apps(t, username, password, self.connection)
        self.neo4j = Neo4jCLI(t, username, password, self.connection)

        self.t = t
        self.url = url
        self.access_token = access_token

        self.logger.info(f"initiated in {time.time()-start}")

        return f"Successfully initialized tapis service on {self.url}"

    @TypeEnforcer.enforcer(recursive=True)
    def accept(self, initial: bool=False):  # function to accept CLI connection to the server
        self.connection, ip_port = self.sock.accept()  # connection request is accepted
        self.logger.info("Received connection request")

        if initial:  # if this is the first time in the session that the cli is connecting
            startup_data = schemas.StartupData(initial = initial)
            self.json_send(startup_data.dict())
            self.logger.info("send the initial status update")

            # give the cli 3 attempts to provide authentication
            for attempt in range(1, 4):
                  # receive the username and password
                url: schemas.StartupData = self.schema_unpack().url
                try:
                # try intializing tapis with the supplied credentials
                    auth_request = schemas.AuthRequest()
                    self.json_send(auth_request.dict())
                    auth_data: schemas.AuthData = self.schema_unpack()
                    username, password = auth_data.username, auth_data.password

                    self.tapis_init(name=url, username=username, password=password)
                    # send to confirm to the CLI that authentication succeeded
                    self.logger.info("Verification success")
                    break
                except Exception as e:
                    print(e)
                    # send failure message to CLI
                    login_failure_data = schemas.ResponseData(response_message = (str(e), attempt))
                    self.json_send(login_failure_data.dict())
                    self.logger.warning("Verification failure")
                    if attempt == 3:  # If there have been 3 login attempts
                        self.logger.error(
                            "Attempted verification too many times. Exiting")
                        os._exit(0)  # shutdown the server
                    continue
        else:
            self.configure_decorators()
        startup_result = schemas.StartupData(initial = initial, username = self.username, url = self.url)
        self.logger.info("Connection success")
        self.json_send(startup_result.dict())
        self.logger.info("Final connection data sent")

    def __exit(self):
        """
        @help: exit the CLI without shutting down the service
        """
        raise exceptions.Exit
    
    def __shutdown(self):
        """
        @help: exit the CLI and shutdown the service
        """
        self.logger.info("Shutdown initiated")
        raise exceptions.Shutdown

    def timeout_handler(self):  # handle timeouts
        if time.time() > self.end_time:  # if the time exceeds the timeout time
            raise exceptions.TimeoutError
    
    def format_help(self, command: dict):
        return f"Command: {command['command_name']}\nDescription:{command['description']}\n{command['syntax']}\n"


    def help(self, command: str):
        """
        @help: returns help information. To get specific help information for tapis services, you can run <service> -c help
        """
        if command in self.help:
            return self.help[command]
        # for command in self.help.values():
        #     help_str += self.format_help(command)
        return self.help

    def run_command(self, command_data: dict):  # process and run commands
        command_group = command_data['command_group']
        if command_group in self.command_group_map:
            command_group = self.command_group_map[command_group]
            return command_group(**command_data)
        elif command_group in self.command_map:
            command = self.command_map[command_group]
            command_data = self.filter_kwargs(command, command_data)
            if command_data:
                return command(**command_data)
            return command()
        else:
            raise exceptions.CommandNotFoundError(command_group)

    def main(self):
        while True: 
            try:
                message = self.schema_unpack()  
                self.timeout_handler()  
                kwargs, exit_status = message.kwargs, message.exit_status
                result = self.run_command(kwargs)
                response = schemas.ResponseData(response_message = result)
                self.end_time = time.time() + 300 
                self.json_send(response.dict()) 
                print(message)
                if exit_status == 1:
                    self.__exit()
            except (exceptions.CommandNotFoundError, exceptions.NoConfirmationError, exceptions.InvalidCredentialsReceived) as e:
                error_response = schemas.ResponseData(response_message = str(e))
                self.json_send(error_response.dict())
            except (exceptions.TimeoutError, exceptions.Shutdown) as e:
                error_response = schemas.ResponseData(response_message = str(e), exit_status=1)
                self.json_send(error_response.dict())
                sys.exit(0)
            except exceptions.Exit as e:
                self.logger.info("user exit initiated")
                error_response = schemas.ResponseData(response_message = str(e), exit_status=1)
                self.json_send(error_response.dict())
                self.connection.close()  # close the connection
                self.accept()  # wait for CLI to reconnect



if __name__ == '__main__':
    server = Server('127.0.0.1', 30000)
    server.main()
