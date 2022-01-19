import sys
import os
import socket
import select
import json
from utils.receive_message import receive_message
from utils.cache import Cache
from utils.security import SSL
from utils.encode_message import encode_message
from utils.chalk import log
from utils.resolve_env import resolve_socket_port, resolve_socket_header_length

# Constants
HEADER_LENGTH = resolve_socket_header_length()
IP = '0.0.0.0'
PORT = resolve_socket_port()

class Server:
    # Constants
    HEADER_LENGTH = ''
    IP = ''
    PORT = ''

    # Variables
    cache = None
    server_socket = None
    sockets_list = []
    socket_mapping = {}


    def __init__(self, header_length: int, ip: str, port: int) -> None:
        '''The __init__ constructor will:
            - Create a socket (socket server)
            - Append the server socket to the "sockets_list" (self.sockets_list) list
        '''
        try:
            self.HEADER_LENGTH = header_length
            self.IP = ip
            self.PORT = port

            # Create the caching database
            cache = Cache()
            cache.create_db()
            self.cache = cache

            # Create the socket
            self.server_socket = self._create_socket()
            self.sockets_list.append(self.server_socket)
            log(f'Listening for connections on {self.IP}:{self.PORT}', 'notification') 
        
        except Exception as ex:
            log(f'General error [3447] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            sys.exit()


    def _create_socket(self) -> socket.socket:
        '''Create socket object.'''
        try:
            # Create the socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind & Listen
            server_socket.bind((self.IP, self.PORT))
            server_socket.listen(30)
            return server_socket
        
        except Exception as ex:
            log(f'General error [5861] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            sys.exit()


    def _send_message(self, message, client_socket: socket.socket) -> bool:
        '''Send messages to sockets. If message doesnt't exist, False value will be returned.'''
        # Make sure message exists
        if message:
            client_socket.send(encode_message(json.dumps(message) if type(message) == dict else message))
            return True
        return False


    def _save_socket(self, socket_id: str, client_socket: socket.socket) -> dict:
        '''Add socket to cache.'''
        try:
            # return self.cache.save_socket(socket_id, client_socket)
            self.socket_mapping[socket_id] = client_socket
            return {'isError': False}
        
        except Exception as ex:
            log(f'General error [1720] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'Failed to save socket'}


    def _get_socket(self, socket_id: str) -> dict:
        '''Get socket from cache.'''
        try:
            # return self.cache.get_socket(socket_id)
            client_socket = self.socket_mapping.get(socket_id, False)
            if not client_socket:
                return {'isError': True, 'message': 'Socket does not exist'}
            return {'isError': False, 'socket': client_socket}
        
        except Exception as ex:
            log(f'General error [8232] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'Failed to get socket'}


    def _remove_socket(self, socket_id: str) -> dict:
        '''Remove socket from cache.'''
        try:
            log(f'Deleting socket: {socket_id}', 'warning')
            # client_socket = self._get_socket(socket_id)['socket'] # get the socket object
            # self.sockets_list.remove(client_socket) # delete the socket with socket object
            # return self.cache.remove_socket(socket_id)
            del self.socket_mapping[socket_id] # delete the socket with socketId
            client_socket = self._get_socket(socket_id)['socket'] # get the socket object
            self.sockets_list.remove(client_socket) # delete the socket with socket object
            return {'isError': False}
                    
        except Exception as ex:
            log(f'General error [4642] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'Failed to remove socket'}


    def _handle_missing_socket(self, missing_socket_id: str, source_socket_id: str, client_socket: socket.socket) -> None:
        '''Notify the requestor socket about missing destination socket.'''
        try:
            log(f'Could not find socket: {missing_socket_id}', 'danger')
            log(f'Sending to socket: {source_socket_id}')  
            self._send_message(
                {
                    'action': 'response',
                    'from': 'server',
                    'to': source_socket_id,
                    'data': {'isError': True, 'message': 'Socket is not registered'},
                }, client_socket
            )
                    
        except Exception as ex:
            log(f'General error [5013] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            

    def _parse_message(self, message: dict) -> tuple:
        '''Parse the essential information from message data.'''
        destination_socket_id = message['to']
        source_socket_id = message['from']
        action = message['action']
        return destination_socket_id, source_socket_id, action


    def _handle_new_client(self) -> bool:
        '''Handle new clients.'''
        try:
            naked_socket, client_address = self.server_socket.accept()
            naked_socket.setblocking(1)
                        
            # Get SSL wrapped socket
            ssl_handler = SSL()
            response = ssl_handler.ssl_wrap_socket(naked_socket) 
            if response['isError']:
                log(response['message'], 'danger')
                return False
            client_socket = response['socket']

            # Validate the client certificate
            response = ssl_handler.validate_cert(client_socket.getpeercert())
            if response['isError']:
                log(response['message'], 'danger')
                return False
            log('Client certificate validated successfully', 'success')

            # Receive message
            message = receive_message(client_socket, self.HEADER_LENGTH)
            if message is False:
                return False

            # Add socket to temporary storage
            self.sockets_list.append(client_socket)

            # Accept the initial socket connection message
            data = json.loads(message['payload'])
            if data['action'] == 'handshake':
                socket_id = data['from']
                self._save_socket(socket_id, client_socket)
                self._send_message(
                    {
                        'action': 'inform',
                        'from': 'server',
                        'to': socket_id,
                        'text': 'Handshake accepted',
                        'level': 'success'
                    }, client_socket
                )

            log(f'Accepted new connection {client_address[0]}:{client_address[1] }', 'notification')
            return True
        
        except Exception as ex:
            log(f'General error [5484] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return False


    def _handle_new_messsage(self, notified_socket: socket.socket) -> bool:
        '''Handle new messages from connected clients.'''
        try:
            message = receive_message(notified_socket, self.HEADER_LENGTH)

            if message is False:
                log(f'Closed connection with socket, socket name: {notified_socket.getsockname()}, peer name: {notified_socket.getpeername()}', 'warning')
                self.sockets_list.remove(notified_socket)
                return False

            # Variables
            data = json.loads(message['payload'])
            destination_socket_id, source_socket_id, action = self._parse_message(data)

            log(f'Received message from {source_socket_id}')

            # When the socket is closing, delete the socket information
            if action == 'deregister':
                self._remove_socket(source_socket_id)
                return False

            # Forward the message to destination sokcet
            response = self._get_socket(destination_socket_id)
            if response['isError']:
                self._handle_missing_socket(destination_socket_id, source_socket_id, notified_socket)
                return False
            destination_socket = response['socket']
                        
            # Send the message to the destination socket
            log(f'Sending to socket: {destination_socket_id}')
            self._send_message(data, destination_socket)

            # Delete the information about the broker socket as it will be terminated
            if action == 'response':
                self._remove_socket(destination_socket_id)
            return True
        
        except Exception as ex:
            log(f'General error [2273] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return False


    def start(self) -> None:
        '''Listen for messages & new clients.'''
        while True:
            read_sockets, _, exception_sockets = select.select(self.sockets_list, [], self.sockets_list)

            for notified_socket in read_sockets:
                # Endpoint connected
                if notified_socket == self.server_socket:
                    self._handle_new_client()

                # Endpoint sent a message
                else:
                    self._handle_new_messsage(notified_socket)

            for notified_socket in exception_sockets:
                self.sockets_list.remove(notified_socket)


    def __repr__(self) -> str:
        return f'Server({self.HEADER_LENGTH}, "{self.IP}", {self.PORT})'


    def __str__(self) -> str:
        return f'Socket server running at {self.IP}:{self.PORT}'


    def __len__(self) -> int:
        return self.HEADER_LENGTH


def main() -> None:
    server = Server(HEADER_LENGTH, IP, PORT)

    # Start the server
    server.start()


if __name__ == '__main__':
    main()