#!/usr/bin/env python

from argparse import ArgumentParser

import pygame as pg
from pygame.locals import QUIT

from redis import Redis

from screen import Screen
from player import Player
from others import Others

# 2 differents speeds
#
# if we do too few frames per second,
# after another player moves, we may see it very late
# (worst case: if FRAME_RATE is 4, then the delay may reach 250ms)
#
# so, we set our frame rate higher; BUT on the other hand
# this also results in the player moving too fast
# so FRAMES_PER_MOVE is defined so we move our player only once every n frames

# how often we redisplay the screen
FRAME_RATE = 10
# we move our player that many times slower
FRAMES_PER_MOVE = 3


def main():

    parser = ArgumentParser()
    # not yet used in the starter code...
    parser.add_argument("-s", "--server", default=None,
                        help="IP adddress for the redis server")
    parser.add_argument("-a", "--auto-move", action="store_true",
                        help="auto move")
    parser.add_argument("name")
    args = parser.parse_args()

    # player's name as provided on the command line
    local_player_name = args.name
    pg.display.set_caption(f"game: {local_player_name}")

    # likewise, at this point args.server can be set from the terminal
    # so you should use it to connect to the redis server
    print(f"This is where we should connect to redis server at {args.server}")

    redis_server=Redis("localhost", decode_responses=True)

    screen = Screen()
    W, H = screen.size()

    clock = pg.time.Clock()

    player = Player(local_player_name, H, W,redis_server)
    others= Others(redis_server)

    # in anticipation for a multi-player version,
    # screen deals with dictionaries, not with player objects
    # this is because the data coming from the redis server
    # will be in the form of dictionaries
    players = [{'color': player.color, 'position': player.position}]
    screen.display(players)

    # type 'a' to toggle auto move
    auto_move = args.auto_move

    counter = 0
    while True:
        # sync with the frame rate
        clock.tick(FRAME_RATE)

        # move the local player
        # actually do all this only once every FRAMES_PER_MOVE frames

        players=others.fetch()
        counter += 1
        if counter % FRAMES_PER_MOVE == 0:
            counter = 0
            if auto_move:
                player.random_move()

            for event in pg.event.get():
                if (event.type == QUIT or
                    (event.type == pg.KEYDOWN and event.key == pg.K_q)):
                    return
                elif event.type == pg.KEYDOWN and event.key == pg.K_a:
                    auto_move = not auto_move
                else:
                    player.handle_event(event)

        # redisplay accordingly every frame
        # same as above, in a multi-player version this will be
        # acquired from the redis server
        players = [{'color': player.color, 'position': player.position}]
        screen.display(players)


if __name__ == '__main__':
    main()
