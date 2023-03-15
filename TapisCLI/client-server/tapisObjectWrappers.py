import json
import os
import re
import sys
import pyperclip
from tapipy import tapis
import tapipy
from py2neo import Graph
import typing
from TypeEnforcement import type_enforcer as t


class tapisObject:
    def __init__(self, tapis_instance, username, password):
        self.t = tapis_instance
        self.username = username
        self.password = password

        dirname = os.path.dirname(__file__)
        root_path = re.findall(r'^(.*?\\TapisCLI)', dirname)[0]
        rel_path = r".\help.json"
        self.help_path = f'{root_path}{rel_path}'

        with open(self.help_path, 'r') as h:
            json_help = h.read()
            self.help = json.loads(json_help)


class Systems(tapisObject):
    def return_formatter(self, info):
        return f"id: {info.id}\nhost: {info.host}\n"

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

    @t.TypeEnforcer.enforcer
    def get_system_info(self, verbose: bool): # get information about a system given its ID
        try:
            system_info = self.t.systems.getSystem(systemId=id)
            if verbose:
                return str(system_info)
            return self.return_formatter(system_info)
        except Exception as e:
            raise e
        
    @t.TypeEnforcer.enforcer
    def create_system(self, file: str, id: str) -> str: # create a tapius system. Takes a path to a json file with all system information, as well as an ID
        with open(file, 'r') as f:
            system = json.loads(f.read())
        self.t.systems.createSystem(**system)
        return str
    
    @t.TypeEnforcer.enforcer
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

    @t.TypeEnforcer.enforcer
    def system_password_set(self, id: str, password: str) -> str: # set the password for a system
        password_return_value = self.t.systems.createUserCredential(systemId=id, # will put this in a getpass later
                            userName=self.username,
                            password=password)
        return str(password_return_value)

    @t.TypeEnforcer.enforcer
    def delete_system(self, id: str) -> str:
        return_value = self.t.systems.deleteSystem(systemId=id)
        return return_value

    @t.TypeEnforcer.enforcer
    def systems_cli(self, **kwargs: dict): # function for managing all of the system commands, makes life easier later
        command = kwargs['command']
        try:
            match command:
                case 'get_systems':
                    return self.get_system_list(**kwargs)
                case 'get_system_info':
                    return self.get_system_info(**kwargs)
                case 'create_system':
                    return self.create_system(**kwargs)
                case "set_credentials":
                    return self.system_credential_upload(**kwargs)
                case "set_password":
                    return self.system_password_set(**kwargs)
                case "delete_system":
                    return self.delete_system(**kwargs)
                case "help":
                    return self.help['systems']
                case _:
                    raise Exception('Command not recognized')
        except IndexError:
            raise Exception("must specify subcommand. See 'help'")


class Neo4jCLI(tapisObject):
    def __init__(self, tapis_object, uname, pword):
        super().__init__(tapis_object, uname, pword)
        self.t = tapis_object
   
    @t.TypeEnforcer.enforcer
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
    def return_formatter(self, info):
        return f"pod_id: {info.pod_id}\npod_template: {info.pod_template}\nurl: {info.url}\nstatus_requested: {info.status_requested}\n\n"

    @t.TypeEnforcer.enforcer
    def get_pods(self, verbose: bool) -> str: # returns a list of pods
        pods_list = self.t.pods.get_pods()
        if verbose:
            return str(pods_list)
        pods_list = [self.return_formatter(pod) for pod in pods_list]
        pods_string = ""
        for pod in pods_list:
            pods_string += str(pod)
        return pods_string
    
    @t.TypeEnforcer.enforcer
    def whoami(self, verbose: bool) -> str: # returns user information
        user_info = self.t.authenticator.get_userinfo()
        if verbose:
            return str(user_info)
        return user_info.username

    @t.TypeEnforcer.enforcer
    def create_pod(self, description: str, id: str, template: str, verbose: bool) -> str: # creates a pod with a pod id, template, and description
        pod_information = self.t.pods.create_pod(pod_id=id, pod_template=template, description=description)
        if verbose:
            return str(pod_information)
        return self.return_formatter(pod_information)

    @t.TypeEnforcer.enforcer
    def restart_pod(self, id: str, verbose: bool) -> str: # restarts a pod if needed
        return_information = self.t.pods.restart_pod(pod_id=id)
        if verbose:
            return str(return_information)
        return self.return_formatter(return_information)

    @t.TypeEnforcer.enforcer
    def delete_pod(self, id: str, verbose: bool) -> str: # deletes a pod
            return_information = self.t.pods.delete_pod(pod_id=id)
            if verbose:
                return str(return_information)
            return self.return_formatter(return_information)

    @t.TypeEnforcer.enforcer
    def set_pod_perms(self, id: str, username: str, level: str) -> str: # set pod permissions, given a pod id, user, and permission level
        return_information = self.t.pods.set_pod_permission(pod_id=id, user=username, level=level)
        return str(return_information)
    
    @t.TypeEnforcer.enforcer
    def delete_pod_perms(self, id: str, username: str) -> str: # take away someones perms if they are being malicious, or something
        return_information = self.t.pods.delete_pod_perms(pod_id=id, user=username)
        return str(return_information)

    @t.TypeEnforcer.enforcer
    def get_perms(self, id: str) -> str: # return a list of permissions on a given pod
        return_information = self.t.pods.get_pod_permissions(pod_id=id)
        return str(return_information)

    @t.TypeEnforcer.enforcer
    def copy_pod_password(self, id: str) -> str: # copies the pod password to clipboard so that the user can access the pod via the neo4j desktop app. Maybe a security risk? not as bad as printing passwords out!
        password = self.t.pods.get_pod_credentials(pod_id=id).user_password
        pyperclip.copy(password)
        password = None
        return 'copied to clipboard'

    @t.TypeEnforcer.enforcer
    def pods_cli(self, **kwargs: dict):
        command = kwargs['command']
        try:
            match command:
                case 'get_pods':
                    return self.get_pods(**kwargs)
                case 'create_pod':
                    return self.create_pod(**kwargs)
                case 'restart_pod':
                    return self.restart_pod(**kwargs)
                case 'delete_pod':
                    return self.delete_pod(**kwargs)
                case "set_pod_perms":
                    return self.set_pod_perms(**kwargs)
                case 'delete_pod_perms':
                    return self.delete_pod_perms(**kwargs)
                case 'get_perms':
                    return self.get_perms(**kwargs)
                case "copy_pod_password":
                    return self.copy_pod_password(**kwargs)
                case "help":
                    return self.help['pods']
                case _:
                    raise Exception(f'Command {command} not recognized')
        except IndexError:
            raise Exception("must specify subcommand. See 'help'")


class Files(tapisObject):
    def return_formatter(self, info):
        return f"name: {info.name}\ngroup: {info.group}\npath: {info.path}\n"

    @t.TypeEnforcer.enforcer
    def list_files(self, verbose: bool, id: str, file: str) -> str: # lists files available on a tapis account
        file_list = self.t.files.listFiles(systemId=id, path=file)
        if verbose:
            return str(file_list)
        file_list = [self.return_formatter(f) for f in file_list]
        return str(file_list)

    @t.TypeEnforcer.enforcer
    def upload(self, file: str, id: str) -> str: # upload a file from local to remote using tapis. Takes source and destination paths
        source = file.split(",")[0]
        destination = file.split(",")[1]
        self.t.upload(system_id=id,
                source_file_path=source,
                dest_file_path=destination)
        return f'successfully uploaded {source} to {destination}'
            
    @t.TypeEnforcer.enforcer
    def download(self, file: str, id: str) -> str: # download a remote file using tapis, operates basically the same as upload
        source = file.split(",")[0]
        destination = file.split(",")[1]
        file_info = self.t.files.getContents(systemId=id,
                            path=source)

        file_info = file_info.decode('utf-8')
        with open(destination, 'w') as f:
            f.write(file_info)
        return f'successfully downloaded {source} to {destination}'

    @t.TypeEnforcer.enforcer
    def files_cli(self, **kwargs: dict): # function to manage all the file commands
        command = kwargs['command']
        try:
            match command:
                case'list_files':
                    return self.list_files(**kwargs)
                case 'upload':
                    return self.upload(**kwargs)
                case 'download':
                    return self.download(**kwargs)
                case "help":
                    return self.help['files']
                case _:
                    raise Exception('Command not recognized')
        except IndexError:
            raise Exception("must specify subcommand. See 'help'")
        except Exception as e:
            raise e


class Apps(tapisObject):
    @t.TypeEnforcer.enforcer
    def create_app(self, file: str) -> str: # create a tapis app taking a json descriptor file path
        with open(file, 'r') as f:
            app_def = json.loads(f.read())
        url = self.t.apps.createAppVersion(**app_def)
        return f"App created successfully\nID: {app_def['id']}\nVersion: {app_def['version']}\nURL: {url}\n"

    @t.TypeEnforcer.enforcer
    def get_apps(self, **kwargs: typing.Any) -> str:
        apps = self.t.apps.getApps()
        return str(apps)

    @t.TypeEnforcer.enforcer
    def delete_app(self, id: str, version: str) -> str:
        return_value = self.t.apps.deleteApp(appId=id, appVersion=version)
        return str(return_value)

    @t.TypeEnforcer.enforcer
    def get_app(self, verbose: bool, id: str, version: str)-> None | str: # returns app information with an id and version as arguments
        app = self.t.apps.getApp(appId=id, appVersion=version)
        if verbose:
            return str(app)
        return None

    @t.TypeEnforcer.enforcer
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

    @t.TypeEnforcer.enforcer
    def get_job_status(self, uuid: str)->str: # return a job status with its Uuid
        job_status = self.t.jobs.getJobStatus(jobUuid=uuid)
        return str(job_status)

    @t.TypeEnforcer.enforcer
    def download_job_output(self, uuid: str, file: str)->str: # download the output of a job with its Uuid
        jobs_output = self.t.jobs.getJobOutputDownload(jobUuid=uuid, outputPath='tapisjob.out')
        with open(file, 'w') as f:
            f.write(jobs_output)
        return f"Successfully downloaded job output to {file}"

    @t.TypeEnforcer.enforcer
    def apps_cli(self, **kwargs: dict): # function to manage all jobs
        command = kwargs['command']
        try:
            match command:
                case 'create_app':
                    return self.create_app(**kwargs)
                case 'get_apps':
                    return self.get_apps(**kwargs)
                case 'delete_app':
                    return self.delete_app(**kwargs)
                case 'get_app_info':
                    return self.get_app(**kwargs)
                case 'run_app':
                    return self.run_job(**kwargs)
                case 'get_app_status':
                    return self.get_job_status(**kwargs)
                case 'download_app_results':
                    return self.download_job_output(**kwargs)
                case "help":
                    return self.help['apps']
                case _:
                    raise Exception('Command not recognized')
        except IndexError:
            raise Exception("must specify subcommand. See 'help'")
        except Exception as e:
            raise e