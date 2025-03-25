import random
import json

import pygame as pg

def random_color():
    return [random.randint(0, 255) for _ in range(3)]

def random_move():
    moves = [(x, y) for x in (-1, 0, 1) for y in (-1, 0, 1) if abs(x+y) == 1]
    return random.choice(moves)



class Player:
    """
    manage the local player, and broadcast
    its position to the redis server
    """

    def __init__(self, name, width, height,server):
        """
        name is the name of the local player
        """
        self.name = name
        self.width = width
        self.height = height
        self.position = [ random.randint(0, self.width-1),
                          random.randint(0, self.height-1)]
        self.color = random_color()
        self.server=server
        


    def random_move(self):
        self.move(*random_move())

    def move(self, dx, dy):
        self.position[0] += dx
        self.position[0] %= self.width
        self.position[1] += dy
        self.position[1] %= self.height
        self.server.hset(self.name, 'position', json.dumps([self.position[0], self.position[1]]))


    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            match event.key:
                case pg.K_UP:
                    self.move(0, -1)
                case pg.K_DOWN:
                    self.move(0, 1)
                case pg.K_RIGHT:
                    self.move(1, 0)
                case pg.K_LEFT:
                    self.move(-1, 0)
                case pg.K_c:
                    self.color = random_color()
                    self.server.hset(self.name, 'color', json.dumps([self.color]))

    def join(self):
        self.server.hset(self.name,mapping = {'position': json.dumps([self.position[0], self.position[1]]),'color': json.dumps([self.color]),})

    def leave(self):
        self.server.delete(self.name)
