import sys
import os
import subprocess
import time
import signal
import socket
import select
import errno
import json
from threading import Thread
from app import task_handler
from utils.receive_message import receive_message
from utils.security import authenticate, SSL
from utils.register_socket import register_socket, deregister_socket
from utils.encode_message import encode_message
from utils.chalk import log
from utils.resolve_env import \
    resolve_socket_server, resolve_socket_port, resolve_socket_header_length, \
    resolve_inputs, resolve_client_readers, resolve_select_timeout, \
    print_agent_info

# Constants
HEADER_LENGTH = resolve_socket_header_length()
IP = resolve_socket_server()
PORT = resolve_socket_port()

class Agent:
    # Constants
    HEADER_LENGTH = ''
    IP = ''
    PORT = ''
    GLOBAL = {
        'token': '',
        'socket_id': ''
    }

    # Variables
    client_socket = None
    client_readers = []


    def __init__(self, header_length: int, ip: str, port: int) -> None:
        '''The __init__ constructor will run when the file is executed.
        Then it will authenticate with the REST API. And save the client socket as an attribute.
        '''
        try:
            self.HEADER_LENGTH = header_length
            self.IP = ip
            self.PORT = port

            print_agent_info()
            self._handle_registration(token=self._handle_authentication())

            connected = False
            while not connected:
                connection = self.connect()
                connected = True if connection else False
        
        except Exception as ex:
            log(f'General error [2665] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            self.cleanup()


    def _handle_authentication(self) -> str:
        '''Authenticate the current user inputs. If failed, the app will close.'''
        try:
            # Inputs
            email, password = resolve_inputs()

            # Authenticate
            log('Socket: Authenticating...', 'warning')
            response = authenticate(email, password)
            if response['isError']:
                log(f'Socket: {response["message"]}', 'danger')
                self.cleanup()

            # If authentication is successful
            log(f'Socket: {response["message"]}', 'success')
            return response['data']['token']
        
        except Exception as ex:
            log(f'General error [7423] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            self.cleanup()


    def _handle_registration(self, token: str) -> str:
        '''Store the socketId in database and return it. If failed, the app will close.'''
        try:
            log('Socket: Registering socket...', 'warning')
            self.GLOBAL['token'] = token
            response = register_socket(token=token, socket_type='agent')
            if response['isError']:
                log(f'Socket: {response["message"]}', 'danger')
                self.cleanup()

            # If socket is registered successfully
            log(f'Socket: {response["message"]}', 'success')
            socket_id = response['data']['socket']['_id']
            self.GLOBAL['socket_id'] = socket_id

            log(f'Socket: {socket_id}', 'notification')
            return socket_id

        except Exception as ex:
            log(f'General error [1773] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            self.cleanup()


    def connect(self) -> bool:
        '''Connect to the socket server. If failed, "False" will be returned.'''
        try:
            log('Socket: Connecting...', 'warning')

            ssl_handler = SSL()
            response = ssl_handler.create_context()
            if response['isError']:
                log(f'Socket: {response["message"]}', 'danger')
                self.cleanup()
            context = response['context']
            naked_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket = context.wrap_socket(naked_socket)
            
            client_socket.connect((self.IP, self.PORT))
            client_socket.setblocking(False)

            response = ssl_handler.validate_cert(client_socket.getpeercert())
            if response['isError']:
                log(f'Socket: {response["message"]}', 'danger')
                self.cleanup()

            self.client_readers = [*resolve_client_readers(), client_socket]
            self.client_socket = client_socket
            self.send_message({
                'action': 'handshake',
                'from': self.GLOBAL['socket_id'],
                'to': 'server'
            })
            
            log('Socket: Connected', 'success')
            return True

        except Exception as ex:
            log('Socket: Connection failed', 'danger')
            time.sleep(4)
            return False


    def cleanup(self) -> None:
        '''Delete socketId from database, and notify the server to remove socket mapping. If failed, the app will close.'''
        try:
            log('Socket: Deregistering socket...', 'warning')
            response = deregister_socket(token=self.GLOBAL['token'], socket_id=self.GLOBAL['socket_id'])
            log(f'REST API: {response["message"]}', 'warning')

            log('Socket: Removing socket mapping...', 'warning')
            self.send_message({
                'action': 'deregister',
                'from': self.GLOBAL['socket_id'],
                'to': 'server',
                'token': self.GLOBAL['token'],
                'data': {}
            })

        except Exception as ex:
            log(f'General error [4648] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')

        finally:
            log(f'Socket: Cleanup complete [{os.path.basename(__file__)}]')
            sys.exit()


    def singal_handler(self, signum, frame) -> None:
        cmd = input('\nReload: R\nTerminate: Q\nnodeagent> ')
        if cmd == 'q' or cmd == 'Q':
            log('Socket: Cleaning up...', 'warning')
            self.cleanup()
        elif cmd == 'r' or cmd == 'R':
            log('Socket: Reloading...')
            deregister_socket(token=self.GLOBAL['token'], socket_id=self.GLOBAL['socket_id'])
            subprocess.call([sys.executable] + [sys.argv[0]])
            # from importlib import reload
            # reload(task_handler)
            log('Socket: Reloaded', 'success')
        else:
            log('Socket: Listening...')
            pass


    def send_message(self, message) -> bool:
        '''Send messages to sockets. If message doesnt't exist, False value will be returned.'''
        # Make sure message exists
        if message:
            self.client_socket.send(encode_message(json.dumps(message) if type(message) == dict else message))
            return True
        return False


    def _handle_request(self, message: dict) -> None:
        '''This function will be handled by threading, as it will allow for multiple messages to be processed simultaneously.'''
        try:
            destination = message['to']
            source = message['from']
            token = message['token']
            data = message['data']

            log(f'Socket: Received message from socket: {source}', 'notification')

            # Run the task
            response = task_handler.handle_task(data)
            log(f'Socket: Sending message to: {source}, from: {destination}')
            self.send_message({
                'action': 'response',
                'from': destination,
                'to': source,
                'token': token,
                'data': response
            })

        except Exception as ex:
            log(f'General error [3416] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')


    def start(self) -> None:
        '''Receive messages. Loop until error.'''
        while True:
            try:
                while True:
                    readers, _, _ = select.select(self.client_readers, [], [], resolve_select_timeout()) # Both STDIN & client_socket have to be readable
                    
                    for reader in readers:
                        if reader is self.client_socket:
                            message = receive_message(self.client_socket, self.HEADER_LENGTH)
                            # Server closed down
                            if message is False:
                                raise socket.error
                            data = json.loads(message['payload'])

                            # If the agent receives an informational message, log the message to the console
                            if data['action'] == 'inform':
                                log(f'Server: {data["text"]}', data['level'])

                            # If the agent received a request from a user. Handle multiple requests asynchronously
                            if data['action'] == 'request':
                                Thread(target=self._handle_request, args=[data]).start()
                        else:
                            sys.stdin.readline()

            except socket.error: # Server closed down, attempt to reconnect
                connected = False
                while not connected:
                    connection = self.connect()
                    connected = True if connection else False

            except IOError as ex:
                # No more messages to be received. OS level
                if ex.errno != errno.EAGAIN and ex.errno != errno.EWOULDBLOCK:
                    log(f'Read error [3949] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
                    self.cleanup()
                continue

            except Exception as ex:
                log(f'General error [1638] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
                self.cleanup()


    def __repr__(self) -> str:
        return f'Agent({self.HEADER_LENGTH}, "{self.IP}", {self.PORT})'


    def __str__(self) -> str:
        return f'Socket connected to server at {self.IP}:{self.PORT}'


    def __len__(self) -> int:
        return self.HEADER_LENGTH


def main() -> None:
    agent = Agent(HEADER_LENGTH, IP, PORT)

    # If quitting the app by "CTRL + C", perform clean-up
    signal.signal(signal.SIGINT, agent.singal_handler)

    # Start the agent
    agent.start()

    # On exit; perform cleanup (in case not caught by the running process)
    agent.cleanup()


if __name__ == '__main__':
    main()