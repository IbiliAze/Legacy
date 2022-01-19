import os
import requests
from utils.chalk import log
from utils.resolve_env import resolve_express_api

def register_socket(token: str, socket_type: str) -> dict:
    '''Save the socketId in a database.'''
    ENDPOINT='/api/socket'
    HOST = resolve_express_api()
        
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        body = {
            'type': socket_type
        }
        response = requests.post(url=f'{HOST}{ENDPOINT}', headers=headers, json=body)
        return {
            'isError': False if response.status_code == 201 else True,
            'message': response.json()['message'],
            'data': response.json()
        }

    except Exception as ex:
        log(f'General error [4061] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True, 'message': 'Failed to register the socket'}


def deregister_socket(token: str, socket_id: str) -> dict:
    '''Delete the socketId from the database.''' 
    ENDPOINT=f'/api/socket/{socket_id}'
    HOST = resolve_express_api()
        
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.delete(url=f'{HOST}{ENDPOINT}', headers=headers)
        return {
            'isError': False if response.status_code == 200 else True,
            'message': response.json()['message'],
            'data': response.json()
        }

    except Exception as ex:
        log(f'General error [8893] [{os.path.basename(__file__)}]: {str(ex)}', 'danger')
        return {'isError': True, 'message': 'Failed to deregister the socket'}