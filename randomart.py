import itertools
from collections import Counter

"""
Implementation of the SSH Randomart visualizer by github.com/fredrik
"""

# the bishop starts in the center of the room
STARTING_POSITION = (8, 4)
ROOM_DIMENSIONS = (17, 9)


# encode start and end positions
COIN_VALUE_STARTING_POSITION = 15
COIN_VALUE_ENDING_POSITION = 16


class Direction(object):
    """Encode a sense of direction."""
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy


NW = Direction(dx=-1, dy=-1)
NE = Direction(dx=1, dy=-1)
SW = Direction(dx=-1, dy=1)
SE = Direction(dx=1, dy=1)


def hex_byte_to_binary(hex_byte):
    """
    Convert a hex byte into a string representation of its bits,
    e.g. 'd4' => '11010100'
    """
    assert len(hex_byte) == 2
    dec = int(hex_byte, 16)
    return bin(dec)[2:].zfill(8)


def bit_pairs(binary):
    """
    Convert a word into bit pairs little-endian style.
    '10100011' => ['11', '00', '10', '10']
    """
    def take(n, iterable):
        "Return first n items of the iterable as a list"
        return list(itertools.islice(iterable, n))
    def all_pairs(iterable):
        while True:
            pair = take(2, iterable)
            if not pair:
                break
            yield ''.join(pair)
    pairs = list(all_pairs(iter(binary)))
    return list(reversed(pairs))


def directions_from_fingerprint(fingerprint):
    """
    Convert the fingerprint (16 hex-encoded bytes separated by colons)
    to steps (one of four directions: NW, NE, SW, SE).
    """
    direction_lookup = {
        '00': NW,
        '01': NE,
        '10': SW,
        '11': SE,
    }
    for hex_byte in [fingerprint[i:i+2] for i in range(0, len(fingerprint), 2)]:
        binary = hex_byte_to_binary(hex_byte)
        # read each bit-pair in each word right-to-left (little endian)
        for bit_pair in bit_pairs(binary):
            direction = direction_lookup[bit_pair]
            yield direction


def move(position, direction):
    """
    Returns new position given current position and direction to move in.
    """
    x, y = position
    MAX_X = ROOM_DIMENSIONS[0] - 1
    MAX_Y = ROOM_DIMENSIONS[1] - 1
    assert 0 <= x <= MAX_X
    assert 0 <= y <= MAX_Y
    nx, ny = x + direction.dx, y + direction.dy
    # the drunk bishop is hindered by the wall.
    nx = 0 if nx <= 0 else min(nx, MAX_X)
    ny = 0 if ny <= 0 else min(ny, MAX_Y)
    return nx, ny


def follow_path(fingerprint):
    room = Counter()
    position = STARTING_POSITION
    for direction in directions_from_fingerprint(fingerprint):
        position = move(position, direction)
        room[position] += 1  # drop coin
    # mark start and end positions
    room[STARTING_POSITION] = COIN_VALUE_STARTING_POSITION
    room[position] = COIN_VALUE_ENDING_POSITION
    return room


def coin(value):
    """
    Display the ascii representation of a coin.
    """
    return {
        0: ' ',
        1: '.',
        2: 'o',
        3: '+',
        4: '=',
        5: '*',
        6: 'B',
        7: 'O',
        8: 'X',
        9: '@',
        10: '%',
        11: '&',
        12: '#',
        13: '/',
        14: '^',
        COIN_VALUE_STARTING_POSITION: 'S',
        COIN_VALUE_ENDING_POSITION: 'E',
    }.get(value, '!')


def display_room(room, title):
    X, Y = ROOM_DIMENSIONS
    room_str = '+' + '-' * X + "+\n"
    for y in range(Y):
        room_str += '|'
        for x in range(X):
            count = room[(x,y)]
            room_str += coin(count)
        room_str += "|\n"
    room_str += '+' + ('[' + title + ']').center(X, '-') + '+'
    return room_str


def randomart(fingerprint, title):
    room = follow_path(fingerprint)
    return display_room(room, title)
