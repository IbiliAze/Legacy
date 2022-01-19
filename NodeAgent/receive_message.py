import os
from utils.chalk import log

def receive_message(client_socket, header_length: int) -> dict:
    '''Receive messages.

    Data will be received in the format: {MESSAGE_HEADER}{MESSAGE}

    Will return False if:
    - Script error
    - No message in body

    Otherwise a dictionary object will be returned as such:
    {
        "header": message_header,
        "payload": client_socket.recv(message_length)
    }
    '''
    try:
        message_header = client_socket.recv(header_length)

        # If we didn't receive a message. Or socket closed the connection
        if not len(message_header):
            return False

        message_length = int(message_header.decode('utf-8').strip())
        message = {
            'header': message_header,
            'payload': client_socket.recv(message_length).decode('utf-8')
        }
        return message

    except Exception as ex:
        log(f'General error [3310] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return False