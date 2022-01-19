import os
import time
import ssl
import requests
from utils.chalk import log
from utils.resolve_env import resolve_express_api

def authenticate(email: str, password: str) -> dict: 
    '''Function for authenticating the JWT Bearer Token with the backend HTTP REST API. 
        - Default URL: https://nodeconfig.com if running in production, or else http://localhost:5000.
        - Endpoint: /api/org/token.
        - Method: POST.
    
    If the response is anything other than 200, then the request (authentication) will be marked as failed.
    '''
    ENDPOINT='/api/org/token'
    HOST = resolve_express_api()
        
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            'email': email,
            'password': password,
            'username': 'nodeconfig-authenticator'
        }
        log(f'Socket: Making request to {HOST}{ENDPOINT}', 'warning')
        response = requests.post(url=f'{HOST}{ENDPOINT}', headers=headers, json=body)

        # If org does not exist, then the authentication failed
        log('Socket: Request successful', 'success')
        return {
            'isError': False if response.status_code == 200 else True,
            'message': response.json()['message'],
            'data': response.json()
        }

    except Exception as ex:
        log(f'General error [7636] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True, 'message': 'Agent Error', 'error': ex}


class SSL:
    def ssl_wrap_socket(self, naked_socket) -> dict:
        '''Wrap socket with SSL.'''
        try:
            # Wrap the socket with SSL
            certs_path = os.path.dirname(os.path.abspath(__file__)).replace('utils', 'certs')
            client_socket = ssl.wrap_socket(
                naked_socket,
                ca_certs=f'{certs_path}/ca/ca-cert.pem',
                certfile=f'{certs_path}/server/server-cert.pem',
                keyfile=f'{certs_path}/server/server-key.pem',
                server_side=True,
                cert_reqs=ssl.CERT_REQUIRED,
                ssl_version=ssl.PROTOCOL_TLSv1_2
            )
            return {'isError': False, 'socket': client_socket}

        except WindowsError as ex:
            log(f'Windows error [2959] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'SSL wrap failed'}

        except Exception as ex:
            log(f'General error [2198] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'SSL wrap failed'}


    def create_context(self) -> dict:
        '''Create an SSL context with the client certificate and private key.'''
        try:
            # Create SSL Context
            context                         = ssl.SSLContext()
            context.verify_mode             = ssl.CERT_REQUIRED
            
            certs_path = os.path.dirname(os.path.abspath(__file__)).replace('utils', 'certs')
            context.load_verify_locations(f'{certs_path}/ca/ca-cert.pem')
            context.load_cert_chain(
                certfile=f'{certs_path}/client/client-cert.pem',
                keyfile=f'{certs_path}/client/client-key.pem'
            )
            return {'isError': False, 'context': context}

        except Exception as ex:
            log(f'General error [9129] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'SSL context creation failed'}


    def validate_cert(self, cert: dict) -> dict:
        '''Validates peer SSL/TLS certificate:
            - Checks if certificate exists
            - Check is commonName is valid
            - Check validity dates
        '''
        try:
            # Validate certificate
            subject                         = dict(item[0] for item in cert['subject']) 
            common_name                     = subject['commonName']

            if not cert:
                return {'isError': True, 'message': 'Unable to retrieve peer certificate'}

            if common_name != 'nodeagent-client' and common_name != 'nodeagent-server':
                return {'isError': True, 'message': 'Incorrect common name in peer certificate'}

            not_after_timestamp             = ssl.cert_time_to_seconds(cert['notAfter'])
            not_before_timestamp            = ssl.cert_time_to_seconds(cert['notBefore'])
            current_time_stamp              = time.time()

            if current_time_stamp > not_after_timestamp:
                return {'isError': True, 'message': 'Expired peer certificate'}
                
            if current_time_stamp < not_before_timestamp:
                return {'isError': True, 'message': 'Peer certificate not yet active'}

            return {'isError': False}

        except Exception as ex:
            log(f'General error [763] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
            return {'isError': True, 'message': 'SSL validation failed'}

            
    def __repr__(self) -> str:
        return 'SSL()'


    def __str__(self) -> str:
        return 'SSL handler for wrapping sockets and certificate validation'
