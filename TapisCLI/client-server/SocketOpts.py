import socket
import json
from TypeEnforcement.type_enforcer import TypeEnforcer
import typing


class SocketOpts:
    @TypeEnforcer.enforcer(recursive=True)
    def json_receive(self) -> str | list | dict: # Receive and unpack json 
        json_data = ""
        while True:
            try: #to handle long files, so that it continues to receive data and create a complete file
                json_data = json_data + self.connection.recv(1024).decode('utf-8') #formulate a full file. Combine sequential data streams to unpack
                return json.loads(json_data) #this is necessary whenever transporting any large amount of data over TCP streams
            except ValueError:
                continue
    
    @TypeEnforcer.enforcer(recursive=True)
    def json_send(self, data: dict | list | str): # package data in json and send
        json_data = json.dumps(data)
        self.connection.send(bytes((json_data), ('utf-8')))