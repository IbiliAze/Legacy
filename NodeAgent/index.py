
import os
import socket
import errno
import json
from dotenv import load_dotenv
from flask import Flask, request
from utils.register_socket import register_socket, deregister_socket
from utils.chalk import log
from utils.security import SSL
from utils.encode_message import encode_message
from utils.resolve_env import resolve_socket_server, resolve_socket_port, resolve_socket_header_length, resolve_flask_port

load_dotenv()
app = Flask(__name__)

HEADER_LENGTH = resolve_socket_header_length()
IP = resolve_socket_server()
PORT = resolve_socket_port()

@app.route('/api/socket', methods=['POST'])
def api_socket():
    '''Data will be received as a JSON payload. 
    To make an initial server-client connection with the agent, we will use sockets.
    
    3 types of sockets will be used:
     - Broker socket: sends the data to the <server socket>
     - Server socket: contains the socket ID to socket mapping caching database
     - Agent socket: performs the task

    The route (REST API) will use the "send_message()" method of the broker, to execute the following:
     - Broker socket establishes a temporary session with the socket server
     - Broker then sends the data over to it with destination socket (agent) ID supplied by the user
     - Server looks into its caching database to find the correct socket (agent) based on the destination socket ID
     - Server forwards the message to the destination socket (agent)
     - Data will be returned to the broker by reversing the destination & source socket ID's
    
    Once the broker socket receives the message from the agent and sends it to the route (REST API response):
     - Broker socket will be shut down
     - The route (REST API) will deregister the broker sokcet
    '''
    data = request.json

    headers = request.headers

    try:
        token = headers['Authorization'].replace('Bearer ', '')

        # Register the socket
        response = register_socket(token, socket_type='broker')
        if response['isError']:
            return response

        # Get the socketId and append to the socket message
        socket_id = response['data']['socket']['_id']
        data['from'] = socket_id
        
        # Send the data to the agent with the broker
        response = send_message(data)

        # Deregister the socket
        deregister_socket(token, socket_id)
        
        return response

    except Exception as ex:
        log(f'General error [195] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True}


def create_socket(socket_id: str) -> dict:
    try:
        # Get SSL Context
        ssl_handler = SSL()
        response = ssl_handler.create_context()
        if response['isError']:
            return {'isError': True, 'message': response['message']}
        context = response['context']
        naked_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket = context.wrap_socket(naked_socket)

        client_socket.connect((IP, PORT))

        response = ssl_handler.validate_cert(client_socket.getpeercert())
        if response['isError']:
            return {'isError': True, 'message': response['message']}

        client_socket.send(encode_message(json.dumps({
            'action': 'handshake',
            'from': socket_id,
            'to': 'server'
        })))
        return {'isError': False, 'socket': client_socket}
    
    except Exception as ex:
        log(f'General error [7379] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True, 'message': 'Failed to create socket'}


def send_message(message: dict) -> dict:
    '''On the event of running a config:
     - The function will receive a message
     - Temporary socket will be created
     - The message will be sent to the agent via the server-broker connection
     - Once the message is received, it will be returned
     - Finally the socket will close (end of while loop)
    '''
    try:
        # Create the socket
        response = create_socket(socket_id=message['from'])
        if response['isError']:
            return response
        
        # Get the socket
        client_socket = response['socket']

        # Make sure message exists
        if message:
            log('Socket: Sending to agent')
            client_socket.send(encode_message(json.dumps(message)))

        while True:
            # Receive messages. Loop until error
            try:
                while True:
                    # Data will be received in the format: {MESSAGE_HEADER}{MESSAGE}
                    message_header = client_socket.recv(HEADER_LENGTH)
                    if not len(message_header):
                        log('Socket: Connection closed by the server', 'danger')
                        return {'isError': True, 'message': 'Broker socket error'}
                    message_length = int(message_header.decode('utf-8').strip())
                    message = json.loads(client_socket.recv(message_length).decode('utf-8'))

                    # If the agent receives an informational message, log the message to the console
                    if message['action'] == 'inform':
                        log(f'Server: {message["text"]}', message['level'])

                    if message['action'] == 'response':
                        log('Socket: Received config response', 'success')
                        log('Socket: Connection terminated by the server', 'warning')
                        return message

            except IOError as ex:
                # No more messages to be received. OS level
                if ex.errno != errno.EAGAIN and ex.errno != errno.EWOULDBLOCK:
                    log(f'Read error [8541] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
                    return {'isError': True, 'message': 'Broker socket read error'}
                continue

            except Exception as ex:
                log(f'General error [2215] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
                return {'isError': True, 'message': 'Broker socket error'}
    
    except Exception as ex:
        log(f'General error [4119] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True, 'message': 'Broker socket error'}


def main():
    app.run(
        host='0.0.0.0',
        port=resolve_flask_port(),
        debug=True if os.environ.get('ENV') == 'dev' else False
    )


if __name__ == '__main__':
    main()
