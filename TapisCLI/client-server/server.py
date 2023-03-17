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
    from . import SocketOpts as SO
except:
    import SocketOpts as SO


class Server(SO.SocketOpts):
    @TypeEnforcer.enforcer(recursive=True)
    def __init__(self, IP: str, PORT: int):
        # logger setup
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler(stream=sys.stdout)

        log_path = r"\logs"
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
        self.username, self.password, self.t, self.url, self.access_token = self.accept(
            initial=True)  # connection returns the tapis object and user info

        # instantiate the subsystems
        self.pods = Pods(self.t, self.username, self.password)
        self.systems = Systems(self.t, self.username, self.password)
        self.files = Files(self.t, self.username, self.password)
        self.apps = Apps(self.t, self.username, self.password)
        self.neo4j = Neo4jCLI(self.t, self.username, self.password)
        self.logger.info('initialization complee')

        self.command_group_map = {
            'pods':self.pods.pods_cli,
            'systems':self.systems.systems_cli,
            'files':self.files.files_cli,
            'apps':self.apps.apps_cli,
            'help':self.help,
            'whoami':self.pods.whoami,
            'exit':self.__exit
        }

    @TypeEnforcer.enforcer(recursive=True)
    def tapis_init(self, username: str, password: str) -> tuple[typing.Any, str, str] | None:  # initialize the tapis opject
        start = time.time()
        base_url = "https://icicle.tapis.io"
        t = Tapis(base_url=base_url,
                  username=username,
                  password=password)
        t.get_tokens()

        # V3 Headers
        header_dat = {"X-Tapis-token": t.access_token.access_token,
                      "Content-Type": "application/json"}

        # Service URL
        url = f"{base_url}/v3"

        # create authenticator for tapis systems
        authenticator = t.access_token
        # extract the access token from the authenticator
        access_token = re.findall(
            r'(?<=access_token: )(.*)', str(authenticator))[0]

        print(type(t))
        return t, url, access_token

    @TypeEnforcer.enforcer(recursive=True)
    def accept(self, initial: bool=False) -> tuple[str, str, typing.Any, str, str]:  # function to accept CLI connection to the server
        self.connection, ip_port = self.sock.accept()  # connection request is accepted
        self.logger.info("Received connection request")
        if initial:  # if this is the first time in the session that the cli is connecting
            # tell the client that it is the first connection
            self.json_send({'connection_type': "initial"})
            # give the cli 3 attempts to provide authentication
            for attempt in range(1, 4):
                credentials = self.json_receive()  # receive the username and password
                self.logger.info("Received credentials")
                username, password = credentials['username'], credentials['password']
                try:
                    # try intializing tapis with the supplied credentials
                    t, url, access_token = self.tapis_init(username, password)
                    # send to confirm to the CLI that authentication succeeded
                    self.json_send([True, attempt])
                    self.logger.info("Verification success")
                    break
                except:
                    # send failure message to CLI
                    self.json_send([False, attempt])
                    self.logger.warning("Verification failure")
                    if attempt == 3:  # If there have been 3 login attempts
                        self.logger.error(
                            "Attempted verification too many times. Exiting")
                        os._exit(0)  # shutdown the server
                    continue
            self.json_send(url)  # send the tapis URL to the CLI
            self.logger.info("Connection success")
            # return the tapis object and credentials
            return username, password, t, url, access_token
        else:  # if this is not the first connection
            # send username, url and connection type
            self.json_send({'connection_type': 'continuing',
                           "username": self.username, "url": self.url})
            self.logger.info("Connection success")

    # handle shutdown scenarios for the server
    @TypeEnforcer.enforcer(recursive=True)
    def shutdown_handler(self, result: str | dict, exit_status: int):
        if result == '[+] Shutting down':  # if the server receives a request to shut down
            self.logger.info("Shutdown initiated")
            sys.exit(0)  # shut down the server
        # if the server receives an exit request
        elif result == '[+] Exiting' or exit_status:
            self.logger.info("user exit initiated")
            self.connection.close()  # close the connection
            self.accept()  # wait for CLI to reconnect

    def timeout_handler(self):  # handle timeouts
        if time.time() > self.end_time:  # if the time exceeds the timeout time
            self.logger.error("timeout. Shutting down")
            self.json_send("[+] Shutting down, Timeout")
            self.connection.close()  # close connection and shutdown server
            os._exit(0)
    
    def help(self):
        with open(r'help.json', 'r') as f:
            return json.load(f)
    
    def __exit(self):
        return "[+] Exiting"
    
    def __shutdown(self):
        return "[+] Shutting down"

    @TypeEnforcer.enforcer(recursive=True)
    def run_command(self, **kwargs):  # process and run commands
        command_group = kwargs['command_group']
        print(kwargs)

    def main(self):
        while True:  # checks if any command line arguments were provided
            try:
                message = self.json_receive()  # receive command request
                self.timeout_handler()  # check if the server has timed out
                # extract info from command
                kwargs, exit_status = message['kwargs'], message['exit']
                result = self.run_command(**kwargs)  # run the command
                self.end_time = time.time() + 300  # reset the timeout
                self.json_send(result)  # send the result to the CLI
                # Handle any shutdown requests
                self.shutdown_handler(result, exit_status)
            except (ConnectionResetError, ConnectionAbortedError, ConnectionError, OSError, WindowsError, socket.error) as e:
                self.logger.error(str(e))
                os._exit(0)
            except Exception as e:
                self.logger.error(str(e))
                self.json_send(str(e))


if __name__ == '__main__':
    server = Server('127.0.0.1', 3000)
    server.main()
