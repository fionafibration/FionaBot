"""
Implementation of the SSH RandomArt generator by natmchugh
github.com/natmchugh
"""

import math

class Atrium(object):

    def __init__(self, bishop, signature):

        self.bishop = bishop
        self.counts = [0] * 153
        self.counts[76] = 15
        self.hashtype = signature


    def move(self, step):
        self.bishop.move(step)
        if self.counts[self.bishop.location()] < 15:
            self.counts[self.bishop.location()] += 1

    def finalise(self, step):
        self.bishop.move(step)
        self.counts[self.bishop.location()] = 16

    def coin(self, count):
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
            15: 'S',
            16: 'E',
            }.get(count)

    def __str__(self):
        output = '+-----------------+\n'
        for idx, val in enumerate(self.counts):
            coin = self.coin(val)
            if idx % 17 == 0:
                output += '|'
            output += coin
            if (idx+1) % 17 == 0:
                output += '|\n'
        hashtype = '['+self.hashtype+']'
        output += '+'+hashtype.center(17, '-')+'+'
        return output


class Bishop(object):

    def __init__(self, pos):
        self.pos = pos

    def coords(self):
        x = self.pos % 17
        y = int(math.floor(self.pos / 17));
        return [x, y]

    def type(self):
        [x, y] = self.coords();
        if y == 0:
            if x == 0:
                return 'a'
            if x == 16:
                return 'b'
            return 'T'
        if x == 0:
            if y == 8:
                return 'c'
            return 'L'
        if x == 16:
            if y == 8:
                return 'd'
            return 'R'
        if y == 8:
            return 'B'
        return 'M'

    def move(self, step):
        w = 0
        squareType = self.type()
        # quite literally corner cases
        if 'a' == squareType:
            w = {
                0: 18,
                1: 17,
                2: 1
            }.get(step, 0)
        if 'b' == squareType:
            w = {
                0: 17,
                1: 16,
                3: 1
            }.get(step, 0)
        if 'c' == squareType:
            w = {
                0: 1,
                2: -16,
                3: -17
            }.get(step, 0)
        if 'd' == squareType:
            w = {
                1: -1,
                2: -17,
                3: -18
            }.get(step, 0)
        if 'R' == squareType and step % 2 == 1:
            w = -1
        if 'T' == squareType and step < 2:
            w = 17
        if 'B' == squareType and step > 1:
            w = -17
        if 'L' == squareType and step % 2 == 0:
            w = 1
        d = {
            0: -18,
            1: -16,
            2: 16,
            3: 18,
        }[step]
        self.pos += d + w

    def location(self):
        return self.pos

class RandomArt(object):

    def __init__(self, hash, signature):
        bishop = Bishop(76)
        self.atrium = Atrium(bishop, signature)
        moves = self.hash_to_moves(hash)
        lastmove = moves.pop()
        for move in moves:
            self.atrium.move(move)
        self.atrium.finalise(lastmove)


    def __str__(self):
        return str(self.atrium)

    def hash_to_moves(self, hash):
        moves =[]
        for word in hash:
            for pair in (3, 2, 1, 0):
                shift = pair*8
                byte = (word & (255 << shift)) >> shift
                for step in range(0, 8, 2):
                  mask = 3 << step
                  move = (byte & mask) >> step
                  moves.append(move)
        return moves