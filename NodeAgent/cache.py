import os
import sqlite3
import socket
from utils.security import SSL
from utils.chalk import log

db_path = os.path.dirname(os.path.abspath(__file__)) + '/socket_mapping.db'

class Cache:
    conn = None
    cursor = None


    def create_db(self) -> dict:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            self.conn = conn
            self.cursor = cursor
            
            cursor.execute('''CREATE TABLE sockets (
                id text,
                fd integer
            )''')
            conn.commit()
            return {'isError': False}

        except Exception as ex:
            log(f'General error [842] [{os.path.basename(__file__)}]: {str(ex)}', level='warning')
            return {'isError': True, 'message': 'Failed to create database'}


    def save_socket(self, id: str, client_socket: socket.socket) -> dict:
        try:
            self.cursor.execute(f"INSERT INTO sockets VALUES ('{id}', {client_socket.fileno()})")
            self.conn.commit()
            return {'isError': False}

        except Exception as ex:
            log(f'General error [1316] [{os.path.basename(__file__)}]: {str(ex)}', level='danger')
            return {'isError': True, 'message': 'Failed to save to cache'}


    def get_socket(self, id: str) -> dict:
        try:
            self.cursor.execute(f"SELECT * FROM sockets WHERE id='{id}'")
            data = self.cursor.fetchone()
            if data == None:
                return {'isError': True, 'message': 'Item does not exist'}
            self.conn.commit()

            fd = int(data[1])

            # Recreate socket + wrap with SSL
            naked_socket = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            ssl_handler = SSL()
            # client_socket = ssl_handler.create_context()['context'].wrap_socket(naked_socket)
            client_socket = ssl_handler.ssl_wrap_socket(naked_socket)['socket']
            return {'isError': False, 'socket': client_socket}

        except Exception as ex:
            log(f'General error [1695] [{os.path.basename(__file__)}]: {str(ex)}', level='danger')
            return {'isError': True, 'message': 'Failed to fetch from cache'}


    def remove_socket(self, id: str) -> dict:
        try:
            self.cursor.execute(f"DELETE * FROM sockets WHERE id='{id}'")
            self.conn.commit()
            return {'isError': False}

        except Exception as ex:
            log(f'General error [3031] [{os.path.basename(__file__)}]: {str(ex)}', level='danger')
            return {'isError': True, 'message': 'Failed to remove from cache'}


    def close_db(self) -> dict:
        try:
            self.conn.close()
            return {'isError': False}

        except Exception as ex:
            log(f'General error [4317] [{os.path.basename(__file__)}]: {str(ex)}', level='danger')
            return {'isError': True, 'message': 'Failed to close database'}


    def __repr__(self) -> str:
        return 'Cache()'


    def __str__(self) -> str:
        return 'Database handler for SQLite3 operations'
