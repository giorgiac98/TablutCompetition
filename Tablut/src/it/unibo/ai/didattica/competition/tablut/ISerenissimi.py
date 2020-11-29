import argparse
import json
from socket import socket, AF_INET, SOCK_STREAM

import numpy as np

from pytablut.game import State
# from pytablut.neuralnet import ResidualNN
from pytablut.player import Player
from pytablut.utils import setup_folders

MAP = {'EMPTY': 0, 'BLACK': -1, 'WHITE': 1, 'KING': 2, 'THRONE': 0,
       'WHITEWIN': 100, 'BLACKWIN': 100, 'DRAW': 100}


class ServerCommunication:
    """ implements communication with the java server """
    WHITE_PORT = 5800
    BLACK_PORT = 5801

    def __init__(self, color, ip_address='localhost'):
        self.color = color
        self.ip_address = ip_address
        self.sock = self.__connect()

    def __connect(self):
        """ performs TCP socket connection with the server"""
        self.sock = socket(AF_INET, SOCK_STREAM)
        if self.color == 'WHITE':
            conn = (self.ip_address, self.WHITE_PORT)
        elif self.color == 'BLACK':
            conn = (self.ip_address, self.BLACK_PORT)
        else:
            raise ValueError('color must be either white or black')
        self.sock.connect(conn)
        return self.sock

    def __json_to_state(self, state):
        board = [list(map(lambda x: MAP[x], row)) for row in state['board']]
        return State(board=np.array(board),
                     turn=MAP[state['turn']])

    def _coord_to_cell(self, coord):
        """
        performs conversion between
        :param coord: (x, y) int indexes of numpy matrix
        :return: a str "CR", where C is the column in [a-i] and R is the row in [1-9]
        """
        return ''.join([chr(coord[1] + 97), str(coord[0] + 1)])

    def execute_move(self, move):
        act = {'from': self._coord_to_cell(move[0]),
               'to': self._coord_to_cell(move[1]),
               'turn': self.color}
        self.write(act)

    def write(self, action):
        """ writes a message to the server """
        tmp = json.dumps(action) + '\r\n'
        msg = bytearray(4 + len(tmp))
        msg[:4] = len(tmp).to_bytes(4, 'big')
        msg[4:] = tmp.encode()
        self.sock.sendall(msg)

    def read(self):
        """ reads a message from the server """
        msg = b''
        msg += self.sock.recv(1024)
        while len(msg) < 1 or chr(msg[-1]) != '}':
            tmp = self.sock.recv(1024)
            if not tmp:
                break
            msg += tmp
            if msg.find(ord('{'), 5) != -1:
                msg = msg[msg.find(ord('{'), 5) - 4:]
        msg = msg[4:].decode()
        json_state = json.loads(msg)
        state = self.__json_to_state(json_state)
        game_over = state.turn not in (1, -1)
        return state, game_over


def play(comm, player):
    # declare name
    comm.write(player.name)
    print('declared name', player.name)
    game_over = False
    while not game_over:
        state, game_over = comm.read()
        print('state received')
        if state.turn == player.color:
            print('my turn')
            move = player.act(state)
            print('move computed')
            comm.execute_move(move)
            print('move executed')
        else:
            print('other player\'s turn')

    if state.turn == 'DRAW':
        print("it\'s a draw")
    elif state.turn == player.color:
        print('I won!')
    else:
        print('I lost')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to launch players.')

    parser.add_argument('color', type=str,
                        help='player color (white/black)')
    parser.add_argument('timeout', type=int,
                        help='timeout in seconds')
    parser.add_argument('ip', type=str,
                        help='server ip address')
    parser.add_argument('-n', '--name', type=str, default='Serenissimo',
                        help='name of the player')
    args = parser.parse_args()
    setup_folders()

    # nnet = ResidualNN()
    p = Player(color=args.color.upper(),
               name=args.name,
               nnet=None,
               timeout=args.timeout)

    c = ServerCommunication(color=args.color.upper(),
                            ip_address=args.ip)
    play(c, p)
