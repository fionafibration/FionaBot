#!/usr/bin/python
# encoding: utf-8

"""
ChessGame: Internal module for use in the FinBot discord bot's chess functions.
"""
import chess
import chess.uci
import chess.pgn
import chess.svg
import cairosvg


class InvalidMoveException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ChessGame:
    def __init__(self):
        self.engine = chess.uci.popen_engine("stockfish_9_x64_popcnt")
        self.engine.uci()
        self.board = chess.Board()
        self.engine.position(self.board)
        self.engine.ucinewgame()

    def player_move(self, movestr):
        self.engine.position(self.board)
        try:
            self.move = chess.Move.from_uci(movestr)
        except ValueError:
            raise InvalidMoveException('That was not a valid UCI move.')
        if self.board.is_legal(self.move):
            self.board.push(self.move)
        else:
            raise InvalidMoveException(self.print_possible_errors(self.move))

    def ai_move(self):
        self.engine.position(self.board)
        self.possible_moves = self.board.legal_moves
        self.response = self.engine.go(searchmoves=self.possible_moves, depth=20)
        self.board.push(self.response[0])

    def generate_move_digest(self, name):
        self.move = self.board.pop()
        self.piece_at_to = self.board.piece_at(self.move.to_square)
        self.piece_at_from = self.board.piece_at(self.move.from_square)
        self.piecemap = ["pawn", "knight", "bishop", "rook", "queen", "king"]
        self.colormap = ["white", "black"]
        self.from_square = ""
        self.to_square = ""
        self.from_square += chr((self.move.from_square % 8) + 97)
        self.from_square += str((self.move.from_square // 8) + 1)
        self.to_square += chr((self.move.to_square % 8) + 97)
        self.to_square += str((self.move.to_square // 8) + 1)
        if self.piece_at_to is None and self.move.promotion is None:
            self.board.push(self.move)
            return "%s moved a %s %s from %s to %s" % \
                   (name, self.colormap[0 if self.piece_at_from.color else 1],
                    self.piecemap[self.piece_at_from.piece_type - 1],
                    self.from_square, self.to_square)
        elif self.piece_at_to is not None and self.move.promotion is None:
            self.board.push(self.move)
            return "%s moved a %s %s from %s to %s capturing a %s %s" % \
                   (name, self.colormap[0 if self.piece_at_from.color else 1],
                    self.piecemap[self.piece_at_from.piece_type - 1], self.from_square, self.to_square,
                    self.colormap[0 if self.piece_at_to.color else 1], self.piecemap[self.piece_at_to.piece_type - 1])
        elif self.piece_at_to is None and self.move.promotion is not None:
            self.board.push(self.move)
            return "%s moved a %s %s from %s to %s and promoted it to a %s" % \
                   (name, self.colormap[0 if self.piece_at_from.color else 1],
                    self.piecemap[self.piece_at_from.piece_type - 1], self.from_square, self.to_square,
                    self.piecemap[self.move.promotion - 1])
        else:
            self.board.push(self.move)
            return "%s moved a %s %s from %s to %s and promoted it to a %s capturing a %s %s" % \
                   (name, self.colormap[0 if self.piece_at_from.color else 1],
                    self.piecemap[self.piece_at_from.piece_type - 1], self.from_square, self.to_square,
                    self.piecemap[self.move.promotion - 1], self.colormap[0 if self.piece_at_to.color else 1],
                    self.piecemap[self.piece_at_to.piece_type - 1])

    def print_possible_errors(self, move):
        if move not in self.board.legal_moves and move in self.board.pseudo_legal_moves:
            return "That move either leaves your king in check or moves him into check. Please try again."
        elif move not in self.board.legal_moves:
            return "That was not a legal move for you. Please try again."
        else:
            return True

    def add_file_ranks(self, board_array, color):
        for i, value in enumerate(board_array[::-1]):
            self.linelist = list(value)
            if color:
                self.linelist.insert(0, str(i + 1) + "  ")
            else:
                self.linelist.insert(0, str(8 - i) + "  ")
            board_array[i] = "".join(self.linelist)
        board_array.reverse()
        if color:
            return "\n".join(board_array) + "\n\n   A B C D E F G H"
        else:
            return "\n".join(board_array) + "\n\n   H G F E D C B A"

    def draw_board(self, color):
        self.board_string = str(self.board)
        self.board_array = self.board_string.split("\n")
        if color:
            return self.add_file_ranks(self.board_array, color)
        else:
            for i, value in enumerate(self.board_array[::-1]):
                self.linelist = list(value)
                self.linelist.reverse()
                self.board_array[i] = "".join(self.linelist)
            return self.add_file_ranks(self.board_array, color)

    def is_finished(self):
        if self.board.is_game_over():
            return True
        return False

    def result(self):
        return self.board.result()

    def check(self):
        return self.board.is_check()

    def get_pgn(self, event='Chess Game', site='The Internet', date="2018", white="Player", black="Stockfish 9"):
        self.pgn = chess.pgn.Game.from_board(self.board)
        self.pgn.headers["Event"] = event
        self.pgn.headers["Site"] = site
        self.pgn.headers["Date"] = date
        self.pgn.headers["Round"] = '1'
        self.pgn.headers["White"] = white
        self.pgn.headers["Black"] = black
        self.pgn.headers["Result"] = self.board.result()
        return str(self.pgn)

    def get_png(self, color):
        try:
            self.lastmove = self.board.peek()
        except IndexError:
            self.lastmove = None
        self.svg = chess.svg.board(self.board, lastmove=self.lastmove, flipped=not color, style="text {fill: white;}")
        return cairosvg.svg2png(bytestring=self.svg.encode('utf-8'))
