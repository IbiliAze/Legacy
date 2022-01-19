from utils.resolve_env import resolve_socket_header_length

def encode_message(message: str, header_length: int = resolve_socket_header_length(), encode_type: str = 'utf-8'):
    '''The function will make the message packet ready for sending across the channel.
    It will add the header value containing the message length.

    Final message example:
     - {HEADER}{MESSAGE}
     - b'12       Hello World'
    
    Required parameters:
     - message

    Optional parameters:
     - header_length
     - encode_type
    '''
    message = message.encode(encode_type)
    message_header = f'{len(message):<{header_length}}'.encode(encode_type)
    return message_header + message