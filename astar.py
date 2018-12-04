import heapq
import math
import io
from PIL import Image, ImageDraw


class PathFindingException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class AStar:
    def __init__(self, array, width, height, start, end):
        self.array = array
        self.width = width
        self.height = height
        self.start = start
        self.end = end

    @staticmethod
    def distance(a, b):
        # Euclidean istance rounded to halves
        return round(math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) * 2) / 2

    def get_neighbors(self, current):
        possible_neighbors = [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]

        neighbors = []

        for dx, dy in possible_neighbors:
            considered = (current[0] + dx, current[1] + dy)
            if 0 <= considered[0] < self.width:
                if 0 <= considered[1] < self.height:
                    if self.array[considered[1]][considered[0]] != 1:
                        neighbors.append(considered)

        return neighbors

    def pathfind(self):
        closed = set()
        came_from = {}
        g_score = {self.start: 0}
        f_score = {self.start: self.distance(self.start, self.end)}
        open = []

        closest = (self.start, g_score[self.start])

        heapq.heappush(open, (f_score[self.start], self.start))

        while open:
            f, current = heapq.heappop(open)

            if current == self.end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(self.start)
                path.reverse()
                return path

            closed.add(current)

            for neighbor in self.get_neighbors(current):
                tentative_g = g_score[current] + self.distance(current, neighbor)

                if neighbor in closed and tentative_g >= g_score.get(neighbor, 0):
                    continue

                if tentative_g < g_score.get(neighbor, 0) or neighbor not in [x[1] for x in open]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self.distance(neighbor, self.end)
                    heapq.heappush(open, (f_score[neighbor], neighbor))
                    if self.distance(neighbor, self.end) < self.distance(closest[0], self.end) or (self.distance(neighbor, self.end) == self.distance(closest[0], self.end) and g_score[neighbor] < closest[1]):
                        closest = (neighbor, g_score[neighbor])

        path = []
        current = closest[0]
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.append(self.start)
        path.reverse()
        return path

    def solve(self):
        solution = self.pathfind()

        def solution_string():
            for y in range(self.height):
                for x in range(self.width):
                    if self.array[y][x] == 1:
                        yield 'B'
                    elif (x, y) in solution:
                        yield '*'
                    else:
                        yield '.'
                yield '\n'
        return ''.join(solution_string()), solution


board = """

..........B.............
.......S..B......BBBBBB.
..........B.....BB......
........BBB.....B..BBBBB
................B.......
................B...X...

""".strip()

board = """

S...
X.

""".strip()

def draw_path(board):
    array = []
    char_array = [[char for char in line] for line in board.split('\n')]

    max_line_length = max(*[len(line) for line in char_array])

    for line in char_array:
        if len(line) < max_line_length:
            line.extend(['.'] * (max_line_length - len(line)))

    if not all([len(row) == len(char_array[0]) for row in char_array]):
        raise PathFindingException('Board is not a rectangle!')

    if not (board.count('S') == 1 and board.count('X') == 1):
        raise PathFindingException('Board must contain a start (S) and end (X) tile!')

    try:
        start = None
        end = None

        width = len(char_array[0])
        height = len(char_array)
        for y in range(height):
            line = []
            for x in range(width):
                if char_array[y][x] == '.':
                    line.append(0)
                elif char_array[y][x] == 'B':
                    line.append(1)
                elif char_array[y][x] == 'S':
                    start = (x, y)
                    line.append(0)
                else:
                    end = (x, y)
                    line.append(0)
            array.append(line)
    except:
        raise PathFindingException('Error parsing board.')
    try:
        a = AStar(array, width, height, start, end)
        solution_board, path = a.solve()

        images = []

        for step in range(len(path)):
            image = Image.new('RGB', (a.width * 12 + 2, a.height * 12 + 2))

            draw = ImageDraw.Draw(image)

            draw.rectangle([0, 0, a.width * 12 + 2, a.height * 12 + 2], fill=(255, 255, 255))
            for y in range(a.height):
                for x in range(a.width):
                    if a.array[y][x] == 1:
                        draw.rectangle([x * 12, y * 12, x * 12 + 12, y * 12 + 12], fill=(0, 0, 0))
                    if (x, y) == a.start:
                        draw.ellipse([x * 12, y * 12, x * 12 + 12, y * 12 + 12], fill=(0, 255, 0))
                    if (x, y) == a.end:
                        draw.ellipse([x * 12, y * 12, x * 12 + 12, y * 12 + 12], fill=(255, 0, 0))
                    if (x, y) == path[step]:
                        draw.ellipse([x * 12, y * 12, x * 12 + 12, y * 12 + 12], fill=(0, 0, 255))
            images.append(image)

        out = io.BytesIO()

        images[0].save(out, format='GIF', save_all=True, append_images=images[1:], duration=300, loop=0)

        return out
    except:
        raise PathFindingException('Error pathfinding or generating GIF')

print(draw_path(board))