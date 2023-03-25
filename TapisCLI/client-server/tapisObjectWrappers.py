import json
import os
import re
import sys
import pyperclip
from tapipy import tapis
import tapipy
from py2neo import Graph
import typing
from TypeEnforcement.type_enforcer import TypeEnforcer
try:
    from . import helpers
except:
    import helpers


class tapisObject(helpers.OperationsHelper):
    def __init__(self, tapis_instance, username, password, command_map):
        self.t = tapis_instance
        self.username = username
        self.password = password

        help_path = r"help.json"
        self.help_path = help_path
        self.command_map = command_map

        with open(self.help_path, 'r') as h:
            json_help = h.read()
            self.help = json.loads(json_help)

    def cli(self, **kwargs):
        command = self.command_map[kwargs['command']]
        kwargs = self.filter_kwargs(command, kwargs)
        return command(**kwargs)


class Systems(tapisObject):
    def __init__(self, tapis_instance, username, password):
        command_map = {
            'get_systems':self.get_system_list,
            'get_system_info':self.get_system_info,
            'create_system':self.create_system,
            'set_credentials':self.system_credential_upload,
            'set_password':self.system_password_set,
            'delete_system':self.delete_system,
            'help':self.__help
        }
        super().__init__(tapis_instance, username, password, command_map)

    def return_formatter(self, info):
        return f"id: {info.id}\nhost: {info.host}\n"

    @TypeEnforcer.enforcer(recursive=True)
    def get_system_list(self, verbose: bool): # return a list of systems active on the account
        try:
            systems = self.t.systems.getSystems()
            if systems and verbose:
                return str(systems)
            elif systems and not verbose:
                systems = [self.return_formatter(system) for system in systems]
                systems_string = ''
                for system in systems:
                    systems_string += system
                return systems_string

            return "[-] No systems registered"
        except Exception as e:
            raise e

    @TypeEnforcer.enforcer(recursive=True)
    def get_system_info(self, verbose: bool): # get information about a system given its ID
        try:
            system_info = self.t.systems.getSystem(systemId=id)
            if verbose:
                return str(system_info)
            return self.return_formatter(system_info)
        except Exception as e:
            raise e
        
    @TypeEnforcer.enforcer(recursive=True)
    def create_system(self, file: str, id: str) -> str: # create a tapius system. Takes a path to a json file with all system information, as well as an ID
        with open(file, 'r') as f:
            system = json.loads(f.read())
        self.t.systems.createSystem(**system)
        return str
    
    @TypeEnforcer.enforcer(recursive=True)
    def system_credential_upload(self, file: str) -> str: # upload key credentials for the system
        with open(file.split(",")[0], 'r') as f:
            private_key = f.read()

        with open(file.split(",")[1], 'r') as f:
            public_key = f.read()

        cred_return_value = self.t.systems.createUserCredential(systemId=id,
                            userName=self.username,
                            privateKey=private_key,
                            publicKey=public_key)

        return str(cred_return_value)

    @TypeEnforcer.enforcer(recursive=True)
    def system_password_set(self, id: str, password: str) -> str: # set the password for a system
        password_return_value = self.t.systems.createUserCredential(systemId=id, # will put this in a getpass later
                            userName=self.username,
                            password=password)
        return str(password_return_value)

    @TypeEnforcer.enforcer(recursive=True)
    def delete_system(self, id: str) -> str:
        return_value = self.t.systems.deleteSystem(systemId=id)
        return return_value

    def __help(self):
        return self.help['systems']


class Neo4jCLI(tapisObject):
    def __init__(self, tapis_object, uname, pword):
        super().__init__(tapis_object, uname, pword)
        self.t = tapis_object
   
    @TypeEnforcer.enforcer(recursive=True)
    def submit_query(self, file: str, id: str) -> str: # function to submit queries to a Neo4j knowledge graph
        uname, pword = self.t.pods.get_pod_credentials(pod_id=id).user_username, self.t.pods.get_pod_credentials(pod_id=id).user_password
        graph = Graph(f"bolt+ssc://{id}.pods.icicle.tapis.io:443", auth=(uname, pword), secure=True, verify=True)
        if file:
            with open(file, 'r') as f:
                expression = f.read()
        
        try:
            return_value = graph.run(expression)
            print(type(return_value))
            if str(return_value) == '(No data)' and 'create' in expression.lower(): # if no data is returned (mostly if something is created) then just say 'success'
                return f'[+][{id}@pods.icicle.tapis.io:443] Success'
            elif str(return_value) == '(No data)':
                return f'[-][{id}@pods.icicle.tapis.io:443] KG is empty'

            return str(f'[+][{id}] {return_value}')
        except Exception as e:
            return str(e)


class Pods(tapisObject):
    def __init__(self, tapis_instance, username, password):
        command_map = {
                'get_pods':self.get_pods,
                'create_pod':self.create_pod,
                'restart_pod':self.restart_pod,
                'delete_pod':self.delete_pod,
                'set_pod_perms':self.set_pod_perms,
                'delete_pod_perms':self.delete_pod_perms,
                'get_perms':self.get_perms,
                'copy_pod_password':self.copy_pod_password,
                'help':self.__help
            }
        super().__init__(tapis_instance, username, password, command_map)

    def return_formatter(self, info):
        return f"pod_id: {info.pod_id}\npod_template: {info.pod_template}\nurl: {info.url}\nstatus_requested: {info.status_requested}\n\n"

    @TypeEnforcer.enforcer(recursive=True)
    def get_pods(self, verbose: bool) -> str: 
        """
        return a list of pods the current tapis instance has access to
        """
        pods_list = self.t.pods.get_pods()
        if verbose:
            return str(pods_list)
        pods_list = [self.return_formatter(pod) for pod in pods_list]
        pods_string = ""
        for pod in pods_list:
            pods_string += str(pod)
        return pods_string
    
    @TypeEnforcer.enforcer(recursive=True)
    def whoami(self, verbose: bool) -> str: # returns user information
        user_info = self.t.authenticator.get_userinfo()
        if verbose:
            return str(user_info)
        return user_info.username

    @TypeEnforcer.enforcer(recursive=True)
    def create_pod(self, description: str, id: str, template: str, verbose: bool) -> str: # creates a pod with a pod id, template, and description
        pod_information = self.t.pods.create_pod(pod_id=id, pod_template=template, description=description)
        if verbose:
            return str(pod_information)
        return self.return_formatter(pod_information)

    @TypeEnforcer.enforcer(recursive=True)
    def restart_pod(self, id: str, verbose: bool) -> str: # restarts a pod if needed
        return_information = self.t.pods.restart_pod(pod_id=id)
        if verbose:
            return str(return_information)
        return self.return_formatter(return_information)

    @TypeEnforcer.enforcer(recursive=True)
    def delete_pod(self, id: str, verbose: bool) -> str: # deletes a pod
        return_information = self.t.pods.delete_pod(pod_id=id)
        if verbose:
            return str(return_information)
        return self.return_formatter(return_information)

    @TypeEnforcer.enforcer(recursive=True)
    def set_pod_perms(self, id: str, username: str, level: str) -> str: # set pod permissions, given a pod id, user, and permission level
        return_information = self.t.pods.set_pod_permission(pod_id=id, user=username, level=level)
        return str(return_information)
    
    @TypeEnforcer.enforcer(recursive=True)
    def delete_pod_perms(self, id: str, username: str) -> str: # take away someones perms if they are being malicious, or something
        return_information = self.t.pods.delete_pod_perms(pod_id=id, user=username)
        return str(return_information)

    @TypeEnforcer.enforcer(recursive=True)
    def get_perms(self, id: str) -> str: # return a list of permissions on a given pod
        return_information = self.t.pods.get_pod_permissions(pod_id=id)
        return str(return_information)

    @TypeEnforcer.enforcer(recursive=True)
    def copy_pod_password(self, id: str) -> str: # copies the pod password to clipboard so that the user can access the pod via the neo4j desktop app. Maybe a security risk? not as bad as printing passwords out!
        password = self.t.pods.get_pod_credentials(pod_id=id).user_password
        pyperclip.copy(password)
        password = None
        return 'copied to clipboard'

    def __help(self):
        return self.help['pods']


class Files(tapisObject):
    def __init__(self, tapis_instance, username, password):
        command_map = {
            'list_files':self.list_files,
            'upload':self.upload,
            'download':self.download,
            'help':self.__help
        }
        super().__init__(tapis_instance, username, password, command_map)

    def return_formatter(self, info):
        return f"name: {info.name}\ngroup: {info.group}\npath: {info.path}\n"

    @TypeEnforcer.enforcer(recursive=True)
    def list_files(self, verbose: bool, id: str, file: str) -> str: # lists files available on a tapis account
        file_list = self.t.files.listFiles(systemId=id, path=file)
        if verbose:
            return str(file_list)
        file_list = [self.return_formatter(f) for f in file_list]
        return str(file_list)

    @TypeEnforcer.enforcer(recursive=True)
    def upload(self, file: str, id: str) -> str: # upload a file from local to remote using tapis. Takes source and destination paths
        source = file.split(",")[0]
        destination = file.split(",")[1]
        self.t.upload(system_id=id,
                source_file_path=source,
                dest_file_path=destination)
        return f'successfully uploaded {source} to {destination}'
            
    @TypeEnforcer.enforcer(recursive=True)
    def download(self, file: str, id: str) -> str: # download a remote file using tapis, operates basically the same as upload
        source = file.split(",")[0]
        destination = file.split(",")[1]
        file_info = self.t.files.getContents(systemId=id,
                            path=source)

        file_info = file_info.decode('utf-8')
        with open(destination, 'w') as f:
            f.write(file_info)
        return f'successfully downloaded {source} to {destination}'
    
    def __help(self):
        return self.help['files']


class Apps(tapisObject):
    def __init__(self, tapis_instance, username, password):
        command_map = {
            'create_app':self.create_app,
            'get_apps':self.get_apps,
            'delete_app':self.delete_app,
            'get_app_info':self.get_app,
            'run_app':self.run_job,
            'get_app_status':self.get_job_status,
            'download_app_results':self.download_job_output,
            'help':self.__help,
        }
        super().__init__(tapis_instance, username, password, command_map)

    @TypeEnforcer.enforcer(recursive=True)
    def create_app(self, file: str) -> str: # create a tapis app taking a json descriptor file path
        with open(file, 'r') as f:
            app_def = json.loads(f.read())
        url = self.t.apps.createAppVersion(**app_def)
        return f"App created successfully\nID: {app_def['id']}\nVersion: {app_def['version']}\nURL: {url}\n"

    @TypeEnforcer.enforcer(recursive=True)
    def get_apps(self, **kwargs: typing.Any) -> str:
        apps = self.t.apps.getApps()
        return str(apps)

    @TypeEnforcer.enforcer(recursive=True)
    def delete_app(self, id: str, version: str) -> str:
        return_value = self.t.apps.deleteApp(appId=id, appVersion=version)
        return str(return_value)

    @TypeEnforcer.enforcer(recursive=True)
    def get_app(self, verbose: bool, id: str, version: str)-> None | str: # returns app information with an id and version as arguments
        app = self.t.apps.getApp(appId=id, appVersion=version)
        if verbose:
            return str(app)
        return None

    @TypeEnforcer.enforcer(recursive=True)
    def run_job(self, file: str, name: str, id: str, version: str)->str: # run a job using an app. Takes a job descriptor json file path
        with open(file, 'r') as f:
            app_args = json.loads(f.read())

        job = {
            "name": name,
            "appId": id, 
            "appVersion": version,
            "parameterSet": {"appArgs": [app_args]        
                            }
        }
        job = self.t.jobs.submitJob(**job)
        return str(job.uuid)

    @TypeEnforcer.enforcer(recursive=True)
    def get_job_status(self, uuid: str)->str: # return a job status with its Uuid
        job_status = self.t.jobs.getJobStatus(jobUuid=uuid)
        return str(job_status)

    @TypeEnforcer.enforcer(recursive=True)
    def download_job_output(self, uuid: str, file: str)->str: # download the output of a job with its Uuid
        jobs_output = self.t.jobs.getJobOutputDownload(jobUuid=uuid, outputPath='tapisjob.out')
        with open(file, 'w') as f:
            f.write(jobs_output)
        return f"Successfully downloaded job output to {file}"

    def __help(self):
        return self.help['apps']