import os
import neat
import pygame, sys
from pygame.locals import *
import random
import math
import matplotlib.pyplot as plt
import CareagaAstar
import numpy

# integer static values

EMPTY = 0
WALL = 1
LAVA = 2
HEALTH = 3
AMMO = 4

# sizes #

screen_width = 1440
screen_height = 900

camera_width = 144
camera_height = 90

map_num_rows = 50
map_num_cols = 50

full_screen_tile_length = 10

# data #

best_fitness = []
gen = 0

# settings #

human_is_playing = False
show_graphics = True

# initialize pygame and window settings

pygame.init()
if show_graphics:
    pygame.display.set_caption('Battle Royale Game')
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = None

# copied code:


def truncate(f, n):
    s = '%.12f' % f
    i, p, d = s.partition('.')
    return '.'.join([i, (d+'0'*n)[:n]])

###############


class AStarAI:
    solution = []
    destination = 0

    def find_solution(self, start_location, game_map_array):

        # input into A* algorithm
        # store path in dictionary

        # convert map to array of 1, 0
        binary_array = []
        for r, row in enumerate(game_map_array):
            binary_array.append([])
            for tile in row:
                if tile == EMPTY:
                    binary_array[r].append(0)
                else:
                    binary_array[r].append(1)

        # find square closest to center of map that is not 1
        found_choice = False
        choice_r = 0
        choice_c = 0
        center_r = int(map_num_rows / 2)
        center_c = int(map_num_cols / 2)
        distance_out = 0
        while not found_choice:
            r = center_r - distance_out
            while r <= center_r + distance_out:
                c = center_c - distance_out
                while c <= center_c + distance_out:
                    if binary_array[r][c] == 0:
                        choice_r = r
                        choice_c = c
                        found_choice = True
                        break
                    c += 1
                r += 1
            distance_out += 1

        self.solution = CareagaAstar.astar(numpy.array(binary_array), tuple(start_location), tuple([choice_r, choice_c]))
        self.destination = len(self.solution) - 1

    def get_next_move(self, player):
        move = [0, 0]
        if self.destination < 0:
            return move
        destination_x = self.solution[self.destination][1] * full_screen_tile_length + full_screen_tile_length / 2
        destination_y = self.solution[self.destination][0] * full_screen_tile_length + full_screen_tile_length / 2

        if player.x != destination_x or player.y != destination_y:
            move[0] = numpy.sign(destination_x - player.x)
            move[1] = numpy.sign(destination_y - player.y)
        else:
            self.destination -= 1
            self.get_next_move(player)

        return move

##############


class Player:
    x = 30
    y = 30
    width = 6
    height = 6
    speed = 1

    health = 100
    ammunition = 10
    weapon_cool_down = 0
    weapon_angle = 0
    is_dead = False

    num_kills = 0

    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y

    def move(self, change_x, change_y, game_map):
        self.x += change_x * self.speed
        self.y += change_y * self.speed

        # check each vertice
        x_direction = -1
        while x_direction <= 1:
            y_direction = -1
            done = False
            while y_direction <= 1:
                tile_col = int(truncate((self.x + x_direction * ((self.width - 0.01) / 2)) / full_screen_tile_length, 0).strip('.'))
                tile_row = int(truncate((self.y + y_direction * ((self.height - 0.01) / 2)) / full_screen_tile_length, 0).strip('.'))
                tile = game_map.game_map_array[tile_row][tile_col]
                if tile == WALL:
                    self.x -= change_x * self.speed
                    self.y -= change_y * self.speed
                y_direction += 2
            x_direction += 2

    def fire_projectile(self):
        self.ammunition -= 1
        self.weapon_cool_down = 10
        return Projectile(self.x, self.y, 2 * math.sin(self.weapon_angle), 2 * math.cos(self.weapon_angle), self)

    def update(self, game_map):
        if self.weapon_cool_down > 0:
            self.weapon_cool_down -= 1
        # check for lava s
        x_direction = -1
        while x_direction <= 1:
            y_direction = -1
            done = False
            while y_direction <= 1:
                vertice_x = self.x + x_direction * ((self.width - 0.01) / 2)
                vertice_y = (self.y + y_direction * ((self.height - 0.01) / 2))
                tile_col = int(truncate(vertice_x / full_screen_tile_length, 0).strip('.'))
                tile_row = int(truncate(vertice_y / full_screen_tile_length, 0).strip('.'))
                tile = game_map.game_map_array[tile_row][tile_col]
                if tile == LAVA:
                    # todo: optimize
                    self.health -= 10
                if tile == HEALTH:
                    self.health += 5
                    if self.health > 100:
                        self.health = 100
                    game_map.game_map_array[tile_row][tile_col] = EMPTY
                if tile == AMMO:
                    self.ammunition += 10
                    game_map.game_map_array[tile_row][tile_col] = EMPTY
                storm_upper_x_bound = map_num_cols * full_screen_tile_length - game_map.storm_advancement
                storm_upper_y_bound = map_num_rows * full_screen_tile_length - game_map.storm_advancement

                if vertice_x > storm_upper_x_bound or vertice_x < game_map.storm_advancement:
                    self.health -= 5
                elif vertice_y > storm_upper_y_bound or vertice_y < game_map.storm_advancement:
                    self.health -= 5

                y_direction += 2
            x_direction += 2

    def draw(self, center_x, center_y):
        # check to see if on screen:
        if center_x - camera_width / 2 < self.x < center_x + camera_width / 2 and center_y - camera_height / 2 < self.y < center_y + camera_height / 2:
            draw_width = self.width * (screen_width / camera_width)
            draw_height = self.height * (screen_height / camera_height)
            middle_x = (self.x - (center_x - camera_width / 2)) * (screen_width / camera_width)
            middle_y = (self.y - (center_y - camera_height / 2)) * (screen_height / camera_height)
            draw_x = (self.x - (center_x - camera_width / 2) - self.width / 2) * (screen_width / camera_width)
            draw_y = (self.y - (center_y - camera_height / 2) - self.height / 2) * (screen_height / camera_height)
            pygame.draw.rect(screen, (0, 255, 0), (draw_x, draw_y, draw_width, draw_height))
            # draw weapon angle
            weapon_end_x = middle_x + (screen_width / camera_width) * 3 * math.sin(self.weapon_angle)
            weapon_end_y = middle_y + (screen_height / camera_height) * 3 * math.cos(self.weapon_angle)
            pygame.draw.line(screen, (0, 0, 0), (middle_x, middle_y), (weapon_end_x, weapon_end_y), 5)


class GameMap:
    game_map_array = []
    storm_advancement = 0
    storm_rate = 5

    def generate_wall_segment(self, row, col, length):
        # todo: undo
        return
        growth_table = []
        y = 0
        while y <= 2:
            growth_table.append([])
            x = 0
            while x <= 2:
                growth_table[y].append(0)
                x += 1
            y += 1
        growth_table[0][1] = 50 - length * 5
        growth_table[1][0] = 50 - length * 5
        growth_table[1][2] = 50 - length * 5
        growth_table[2][1] = 50 - length * 5

        self.game_map_array[row][col] = WALL

        y = 0
        while y <= 2:
            growth_table.append([])
            x = 0
            while x <= 2:
                wall_gen_prob = random.randint(0, 100)
                if growth_table[x][y] >= wall_gen_prob:
                    next_row = row + (y - 1)
                    next_col = col + (x - 1)
                    if 0 < next_row < map_num_rows and 0 < next_col < map_num_cols:
                        self.generate_wall_segment(next_row, next_col, length + 1)
                x += 1
            y += 1

    def generate_lava_segment(self, row, col, length):
        growth_table = []
        y = 0
        while y <= 2:
            growth_table.append([])
            x = 0
            while x <= 2:
                growth_table[y].append(0)
                x += 1
            y += 1
        growth_table[0][1] = 30 - length * 5
        growth_table[1][0] = 30 - length * 5
        growth_table[1][2] = 30 - length * 5
        growth_table[2][1] = 30 - length * 5

        self.game_map_array[row][col] = LAVA

        y = 0
        while y <= 2:
            growth_table.append([])
            x = 0
            while x <= 2:
                wall_gen_prob = random.randint(0, 100)
                if growth_table[x][y] >= wall_gen_prob:
                    next_row = row + (y - 1)
                    next_col = col + (x - 1)
                    if 0 < next_row < map_num_rows and 0 < next_col < map_num_cols:
                        self.generate_lava_segment(next_row, next_col, length + 1)
                x += 1
            y += 1

    def __init__(self) -> None:
        self.game_map_array = []

        row = 0
        while row < map_num_rows:
            self.game_map_array.append([])
            col = 0
            while col < map_num_cols:
                self.game_map_array[row].append(EMPTY)
                col += 1
            row += 1
        row = 0

        while row < map_num_rows:
            col = 0
            while col < map_num_cols:
                square_choice = random.randint(0, 100)
                if square_choice < 1:
                    self.generate_wall_segment(row, col, 0)
                elif square_choice < 5:
                    self.generate_lava_segment(row, col, 0)
                elif square_choice < 5:
                    if self.game_map_array[row][col] == EMPTY:
                        # todo: undo
                        i = 1
                        # self.game_map_array[row][col] = HEALTH
                elif square_choice < 6:
                    if self.game_map_array[row][col] == EMPTY:
                        # todo: undo
                        i = 1
                        # self.game_map_array[row][col] = AMMO
                col += 1
            row += 1

        # create border
        # top
        row = 0
        col = 0
        while col < map_num_cols:
            self.game_map_array[row][col] = WALL
            col += 1
        # left
        row = 0
        col = 0
        while row < map_num_rows:
            self.game_map_array[row][col] = WALL
            row += 1
        # right
        row = 0
        col = map_num_cols - 1
        while row < map_num_rows:
            self.game_map_array[row][col] = WALL
            row += 1
        # bottom
        row = map_num_rows - 1
        col = 0
        while col < map_num_cols:
            self.game_map_array[row][col] = WALL
            col += 1

        # create spawn area
        # left
        row = 1
        while row < map_num_rows - 1:
            col = 1
            while col < 5:
                self.game_map_array[row][col] = EMPTY
                col += 1
            row += 1
        # top
        col = 1
        while col < map_num_cols - 1:
            row = 1
            while row < 5:
                self.game_map_array[row][col] = EMPTY
                row += 1
            col += 1
        # right
        row = 1
        while row < map_num_rows - 1:
            col = map_num_cols - 5
            while col < map_num_cols - 1:
                self.game_map_array[row][col] = EMPTY
                col += 1
            row += 1
        # bottom
        col = 1
        while col < map_num_cols - 1:
            row = map_num_rows - 5
            while row < map_num_rows - 1:
                self.game_map_array[row][col] = EMPTY
                row += 1
            col += 1

    def draw(self, center_x, center_y):
        adjusted_tile_length = full_screen_tile_length * (screen_width / camera_width)
        map_y = center_y - camera_height / 2
        y = 0
        while y < screen_height:
            map_x = center_x - camera_width / 2
            x = 0
            # figure out what height should be
            tile_height = adjusted_tile_length
            if y == 0:
                tile_height = (full_screen_tile_length - map_y % full_screen_tile_length) / full_screen_tile_length * adjusted_tile_length
            if y + adjusted_tile_length > screen_height:
                tile_height = screen_height - y
            if tile_height == 0:
                tile_height = adjusted_tile_length
            while x < screen_width:
                # figure out what width should be
                tile_width = adjusted_tile_length
                if x == 0:
                    tile_width = (full_screen_tile_length - map_x % full_screen_tile_length) / full_screen_tile_length * adjusted_tile_length
                if x + adjusted_tile_length > screen_width:
                    tile_width = screen_width - x

                if tile_width == 0:
                    tile_width = adjusted_tile_length

                # figure out what tile i'm on
                tile_col = int(truncate((map_x / screen_width) * 144, 0).strip('.'))
                tile_row = int(truncate((map_y / screen_height) * 90, 0).strip('.'))

                if (not (0 <= tile_col < map_num_cols and 0 <= tile_row < map_num_rows)) or map_x < 0 or map_y < 0:
                    tile = EMPTY
                else:
                    tile = self.game_map_array[tile_row][tile_col]

                if tile == EMPTY:
                    pygame.draw.rect(screen, (255, 255, 255), (x, y, tile_width + 1, tile_height + 1))
                elif tile == WALL:
                    pygame.draw.rect(screen, (0, 0, 0), (x, y, tile_width + 1, tile_height + 1))
                elif tile == LAVA:
                    pygame.draw.rect(screen, (255, 0, 0), (x, y, tile_width + 1, tile_height + 1))
                elif tile == HEALTH:
                    pygame.draw.rect(screen, (255, 255, 255), (x, y, tile_width + 1, tile_height + 1))
                    health_kit_image = pygame.image.load("health_kit.png")
                    health_kit_image = pygame.transform.scale(health_kit_image, (int(adjusted_tile_length), int(adjusted_tile_length)))
                    if x == 0 and y == 0:
                        screen.blit(health_kit_image, (x - (adjusted_tile_length - tile_width), y - (adjusted_tile_length - tile_height)))
                    elif x == 0:
                        screen.blit(health_kit_image, (x - (adjusted_tile_length - tile_width), y))
                    elif y == 0:
                        screen.blit(health_kit_image, (x, y - (adjusted_tile_length - tile_height)))
                    else:
                        screen.blit(health_kit_image, (x, y))
                elif tile == AMMO:
                    pygame.draw.rect(screen, (255, 255, 255), (x, y, tile_width + 1, tile_height + 1))
                    ammo_image = pygame.image.load("ammo.png")
                    ammo_image = pygame.transform.scale(ammo_image,(int(adjusted_tile_length), int(adjusted_tile_length)))
                    if x == 0 and y == 0:
                        screen.blit(ammo_image, (x - (adjusted_tile_length - tile_width), y - (adjusted_tile_length - tile_height)))
                    elif x == 0:
                        screen.blit(ammo_image, (x - (adjusted_tile_length - tile_width), y))
                    elif y == 0:
                        screen.blit(ammo_image, (x, y - (adjusted_tile_length - tile_height)))
                    else:
                        screen.blit(ammo_image, (x, y))

                pygame.draw.rect(screen, (0, 0, 0), (x, y, 3, 3))
                if tile_row == map_num_rows / 2 and tile_col == map_num_cols / 2:
                    pygame.draw.rect(screen, (0, 0, 0), (x, y, 6, 6))

                # update values
                x += tile_width
                map_x += full_screen_tile_length

            # update values
            y += tile_height
            map_y += full_screen_tile_length

            # draw storm
            if center_x - camera_width / 2 < self.storm_advancement:
                pygame.draw.rect(screen, (213, 68, 242), (0, 0, ((self.storm_advancement - (center_x - camera_width / 2)) * screen_width / camera_width), screen_height))
            if center_y - camera_height / 2 < self.storm_advancement:
                pygame.draw.rect(screen, (213, 68, 242), (0, 0, screen_width, ((self.storm_advancement - (center_y - camera_height / 2)) * screen_height / camera_height)))
            if center_x + camera_width / 2 > map_num_cols * full_screen_tile_length - self.storm_advancement:
                storm_width = ((center_x + camera_width / 2) - (map_num_cols * full_screen_tile_length - self.storm_advancement)) * (screen_width / camera_width)
                pygame.draw.rect(screen, (213, 68, 242), (screen_width - storm_width, 0, storm_width + 1, screen_height))
            if center_y + camera_height / 2 > map_num_rows * full_screen_tile_length - self.storm_advancement:
                storm_height = ((center_y + camera_height / 2) - (map_num_rows * full_screen_tile_length - self.storm_advancement)) * (screen_height / camera_height)
                pygame.draw.rect(screen, (213, 68, 242), (0, screen_height - storm_height, screen_width, storm_height + 1))


class Projectile:
    radius = 1
    x = 0
    y = 0
    x_vel = 0
    y_vel = 0
    owner = None

    is_gone = False

    def __init__(self, x, y, x_vel, y_vel, owner) -> None:
        self.x = x
        self.y = y
        self.x_vel = x_vel
        self.y_vel = y_vel
        self.owner = owner

    def update(self, game_map):
        self.x += self.x_vel
        self.y += self.y_vel
        game_map_col = int(truncate(self.x / full_screen_tile_length, 0).strip("."))
        game_map_row = int(truncate(self.y / full_screen_tile_length, 0).strip("."))
        if game_map.game_map_array[game_map_row][game_map_col] == WALL:
            self.is_gone = True

    def draw(self, center_x, center_y):
        if center_x - camera_width / 2 < self.x < center_x + camera_width / 2 and center_y - camera_height / 2 < self.y < center_y + camera_height / 2:
            screen_x = int((self.x - (center_x - camera_width / 2)) * (screen_width / camera_width))
            screen_y = int((self.y - (center_y - camera_height / 2)) * (screen_height / camera_height))
            pygame.draw.circle(screen, (200, 200, 200), (screen_x, screen_y), int(self.radius * (screen_width / camera_width)))


def get_spawn_locations():
    possible_spawn_locations = []
    # top
    row = 3
    col = 3
    while col < map_num_cols:
        possible_spawn_locations.append([row, col])
        col += 3
    # bottom
    row = map_num_rows - 3
    col = 3
    while col < map_num_cols:
        possible_spawn_locations.append([row, col])
        col += 3
    # left
    row = 5
    col = 3
    while row < map_num_rows - 5:
        possible_spawn_locations.append([row, col])
        row += 3
    # right
    row = 5
    col = map_num_cols - 3
    while row < map_num_rows - 5:
        possible_spawn_locations.append([row, col])
        row += 3
    return possible_spawn_locations


def get_player_fitness_a_star(genomes, config):
    global gen
    gen += 1

    # clock for game
    main_clock = pygame.time.Clock()

    # map
    game_map = GameMap()


    # players
    possible_spawn_locations = get_spawn_locations()

    nets = []
    ge = []
    players = []
    ais = []
    for _, g in genomes:
        choice = random.randint(0, len(possible_spawn_locations) - 1)
        player_x = full_screen_tile_length * possible_spawn_locations[choice][1] + 5
        player_y = full_screen_tile_length * possible_spawn_locations[choice][0] + 5
        players.append(Player(player_x, player_y))
        net = neat.nn.FeedForwardNetwork.create(g, config)
        ai = AStarAI()
        ai.find_solution(possible_spawn_locations[choice], game_map.game_map_array)
        ai.solution.append(possible_spawn_locations[choice])
        ais.append(ai)
        nets.append(net)
        g.fitness = 0
        ge.append(g)

    human_player = None
    if human_is_playing:
        choice = random.randint(0, len(players) - 1)
        human_player = players[choice]

    # player to spectate if human is dead/not playing
    spectate_player = players[0]
    if human_is_playing:
        spectate_player = human_player

    # list of projectiles
    projectile_list = []

    # get camera dimensions from outer scope
    global camera_width
    global camera_height

    game_is_active = True
    game_ticks = 0

    while game_is_active:
        game_ticks += 1
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[K_ESCAPE]:
            pygame.quit()
            sys.exit()
        if keys[K_MINUS]:
            camera_width = camera_width * 1.02
            camera_height = camera_height * 1.02
        if keys[K_EQUALS]:
            camera_width = camera_width * 0.98
            camera_height = camera_height * 0.98

        if human_is_playing and not human_player.is_dead:
            if keys[K_UP]:
                human_player.move(0, -1, game_map)
            if keys[K_DOWN]:
                human_player.move(0, 1, game_map)
            if keys[K_LEFT]:
                human_player.move(-1, 0, game_map)
            if keys[K_RIGHT]:
                human_player.move(1, 0, game_map)
            if keys[K_SPACE]:
                if human_player.ammunition > 0 and human_player.weapon_cool_down == 0:
                    projectile_list.append(human_player.fire_projectile())
            if keys[K_z]:
                human_player.weapon_angle += 0.1
            if keys[K_x]:
                human_player.weapon_angle -= 0.1

        # inputs:
        '''
            add later
            - x_displacement
            - y_displacement
            - list of squares
            - health

            only use these for now
            - storm distance
            - x location
            - y location
        '''

        for n, player in enumerate(players):

            # find what square player is on
            square_row = int(truncate(player.y / full_screen_tile_length, 0).strip("."))
            square_col = int(truncate(player.x / full_screen_tile_length, 0).strip("."))

            # find displacement
            x_displacement = player.x - square_col * full_screen_tile_length
            y_displacement = player.y - square_row * full_screen_tile_length

            # find squares
            squares = []
            row = square_row - 1
            while row <= square_row + 1:
                col = square_col - 1
                while col <= square_col + 1:
                    if 0 <= row < map_num_rows and 0 <= col < map_num_cols:
                        squares.append(game_map.game_map_array[row][col])
                    else:
                        squares.append(EMPTY)
                    col += 1
                row += 1

            # health, storm increment, x location, y location
            # health = player.health
            # storm_advancement = game_map.storm_advancement
            x_location = player.x
            y_location = player.y
            input_list = [x_location, y_location, x_displacement, y_displacement] + squares
            # input_list.append(x_displacement)
            # input_list.append(y_displacement)
            # input_list.append(health)

            if player is not human_player:
                # output = nets[n].activate(tuple(input_list))
                #
                # # output 0: decide to (go up or down) or (not move)
                # # output 1: decide to (go up) or (go down)
                # # output 2: decide to (go right or left) or (not move)
                # # output 3: decide to (go right) or (go left)
                #
                # if output[0] > 0.5:
                #     if output[1] > 0.5:
                #         player.move(0, -1, game_map)
                #     else:
                #         player.move(0, 1, game_map)
                #
                # if output[2] > 0.5:
                #     if output[3] > 0.5:
                #         player.move(1, 0, game_map)
                #     else:
                #         player.move(-1, 0, game_map)

                output = ais[n].get_next_move(player)

                player.move(output[0], output[1], game_map)

        # update everything

        if game_ticks % game_map.storm_rate == 0:
            game_map.storm_advancement += 1

        for n, player in enumerate(players):
            player.update(game_map)
            # fitness based on how long players survive
            ge[n].fitness += 1
            if player.health <= 0:
                player.is_dead = True
                # map_width = map_num_cols * full_screen_tile_length
                # map_height = map_num_rows * full_screen_tile_length
                # full_euclidean_distance = math.sqrt((map_width / 2) ** 2 + (map_height / 2) ** 2)
                # player_euclidean_distance = math.sqrt((player.x - map_width / 2) ** 2 + (player.y - map_height / 2) ** 2)
                # ge[n].fitness = full_euclidean_distance - player_euclidean_distance
                ais.pop(n)
                players.pop(n)
                nets.pop(n)
                ge.pop(n)

        if len(players) == 0:
            break

        if spectate_player.is_dead:
            spectate_player = players[0]

        for n, projectile in enumerate(projectile_list):
            projectile.update(game_map)
            if projectile.is_gone:
                projectile_list.pop(n)

        # check projectile collisions
        for n, projectile in enumerate(projectile_list):
            for x, player in enumerate(players):
                if player is not projectile.owner and abs(player.x - projectile.x) < 3 and abs(
                        player.y - projectile.y) < 3:
                    player.health -= 10
                    if player.health <= 0:
                        projectile.owner.num_kills += 1
                    projectile_list.pop(n)
                    break

        if show_graphics:
            # draw everything
            game_map.draw(spectate_player.x, spectate_player.y)
            for player in players:
                player.draw(spectate_player.x, spectate_player.y)
            for projectile in projectile_list:
                projectile.draw(spectate_player.x, spectate_player.y)
            # labels
            pygame.draw.rect(screen, (0, 0, 0), (1180, 80, 200, 180))
            fps = main_clock.get_fps()
            my_font = pygame.font.SysFont("monospace", 50)
            fps_label = my_font.render("fps: " + str(round(fps)), 1, (0, 0, 255))
            screen.blit(fps_label, (1200, 100))
            num_kills_label = my_font.render("kills: " + str(spectate_player.num_kills), 1, (0, 0, 255))
            screen.blit(num_kills_label, (1200, 150))
            ammo_label = my_font.render("ammo: " + str(spectate_player.ammunition), 1, (0, 0, 255))
            screen.blit(ammo_label, (1200, 200))
            # health bar
            pygame.draw.rect(screen, (0, 255, 0), ((screen_width / 2) - 300, 30, 600, 20))
            missing_health_x = (screen_width / 2) + 300 - ((100 - spectate_player.health) / 100) * 600
            pygame.draw.rect(screen, (255, 0, 0),
                             (missing_health_x, 30, ((100 - spectate_player.health) / 100) * 600, 20))
            pygame.draw.rect(screen, (0, 0, 0), ((screen_width / 2) - 300, 30, 600, 20), 5)
            main_clock.tick(60)
            pygame.display.update()


def get_player_fitness(genomes, config):
    global gen
    gen += 1

    # clock for game
    main_clock = pygame.time.Clock()

    # map
    game_map = GameMap()

    # players
    possible_spawn_locations = get_spawn_locations()

    nets = []
    ge = []
    players = []
    for _, g in genomes:
        choice = random.randint(0, len(possible_spawn_locations) - 1)
        player_x = full_screen_tile_length * possible_spawn_locations[choice][1]
        player_y = full_screen_tile_length * possible_spawn_locations[choice][0]
        players.append(Player(player_x, player_y))
        net = neat.nn.FeedForwardNetwork.create(g, config)
        nets.append(net)
        g.fitness = 0
        ge.append(g)

    human_player = None
    if human_is_playing:
        choice = random.randint(0, len(players) - 1)
        human_player = players[choice]

    # player to spectate if human is dead/not playing
    spectate_player = players[0]
    if human_is_playing:
        spectate_player = human_player

    # list of projectiles
    projectile_list = []

    # get camera dimensions from outer scope
    global camera_width
    global camera_height

    game_is_active = True
    game_ticks = 0

    while game_is_active:
        game_ticks += 1
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[K_ESCAPE]:
            pygame.quit()
            sys.exit()
        if keys[K_MINUS]:
            camera_width = camera_width * 1.02
            camera_height = camera_height * 1.02
        if keys[K_EQUALS]:
            camera_width = camera_width * 0.98
            camera_height = camera_height * 0.98

        if human_is_playing and not human_player.is_dead:
            if keys[K_UP]:
                human_player.move(0, -1, game_map)
            if keys[K_DOWN]:
                human_player.move(0, 1, game_map)
            if keys[K_LEFT]:
                human_player.move(-1, 0, game_map)
            if keys[K_RIGHT]:
                human_player.move(1, 0, game_map)
            if keys[K_SPACE]:
                if human_player.ammunition > 0 and human_player.weapon_cool_down == 0:
                    projectile_list.append(human_player.fire_projectile())
            if keys[K_z]:
                human_player.weapon_angle += 0.1
            if keys[K_x]:
                human_player.weapon_angle -= 0.1

        # inputs:
        '''
            add later
            - x_displacement
            - y_displacement
            - list of squares
            - health
            
            only use these for now
            - storm distance
            - x location
            - y location
        '''

        for n, player in enumerate(players):

            # find what square player is on
            square_row = int(truncate(player.y / full_screen_tile_length, 0).strip("."))
            square_col = int(truncate(player.x / full_screen_tile_length, 0).strip("."))

            # find displacement
            x_displacement = player.x - square_col * full_screen_tile_length
            y_displacement = player.y - square_row * full_screen_tile_length

            # find squares
            squares = []
            row = square_row - 1
            while row <= square_row + 1:
                col = square_col - 1
                while col <= square_col + 1:
                    if 0 <= row < map_num_rows and 0 <= col < map_num_cols:
                        squares.append(game_map.game_map_array[row][col])
                    else:
                        squares.append(EMPTY)
                    col += 1
                row += 1

            # health, storm increment, x location, y location
            # health = player.health
            # storm_advancement = game_map.storm_advancement
            x_location = player.x
            y_location = player.y
            input_list = [x_location, y_location, x_displacement, y_displacement] + squares
            # input_list.append(x_displacement)
            # input_list.append(y_displacement)
            # input_list.append(health)

            if player is not human_player:
                output = nets[n].activate(tuple(input_list))

                # output 0: decide to (go up or down) or (not move)
                # output 1: decide to (go up) or (go down)
                # output 2: decide to (go right or left) or (not move)
                # output 3: decide to (go right) or (go left)

                if output[0] > 0.5:
                    if output[1] > 0.5:
                        player.move(0, -1, game_map)
                    else:
                        player.move(0, 1, game_map)

                if output[2] > 0.5:
                    if output[3] > 0.5:
                        player.move(1, 0, game_map)
                    else:
                        player.move(-1, 0, game_map)

        # update everything

        if game_ticks % game_map.storm_rate == 0:
            game_map.storm_advancement += 1

        for n, player in enumerate(players):
            player.update(game_map)
            # fitness based on how long players survive
            ge[n].fitness += 1
            if player.health <= 0:
                player.is_dead = True
                # map_width = map_num_cols * full_screen_tile_length
                # map_height = map_num_rows * full_screen_tile_length
                # full_euclidean_distance = math.sqrt((map_width / 2) ** 2 + (map_height / 2) ** 2)
                # player_euclidean_distance = math.sqrt((player.x - map_width / 2) ** 2 + (player.y - map_height / 2) ** 2)
                # ge[n].fitness = full_euclidean_distance - player_euclidean_distance
                players.pop(n)
                nets.pop(n)
                ge.pop(n)

        if len(players) == 0:
            break

        if spectate_player.is_dead:
            spectate_player = players[0]

        for n, projectile in enumerate(projectile_list):
            projectile.update(game_map)
            if projectile.is_gone:
                projectile_list.pop(n)

        # check projectile collisions
        for n, projectile in enumerate(projectile_list):
            for x, player in enumerate(players):
                if player is not projectile.owner and abs(player.x - projectile.x) < 3 and abs(player.y - projectile.y) < 3:
                    player.health -= 10
                    if player.health <= 0:
                        projectile.owner.num_kills += 1
                    projectile_list.pop(n)
                    break

        if show_graphics:
            # draw everything
            game_map.draw(spectate_player.x, spectate_player.y)
            for player in players:
                player.draw(spectate_player.x, spectate_player.y)
            for projectile in projectile_list:
                projectile.draw(spectate_player.x, spectate_player.y)
            # labels
            pygame.draw.rect(screen, (0, 0, 0), (1180, 80, 200, 180))
            fps = main_clock.get_fps()
            my_font = pygame.font.SysFont("monospace", 50)
            fps_label = my_font.render("fps: " + str(round(fps)), 1, (0, 0, 255))
            screen.blit(fps_label, (1200, 100))
            num_kills_label = my_font.render("kills: " + str(spectate_player.num_kills), 1, (0, 0, 255))
            screen.blit(num_kills_label, (1200, 150))
            ammo_label = my_font.render("ammo: " + str(spectate_player.ammunition), 1, (0, 0, 255))
            screen.blit(ammo_label, (1200, 200))
            # health bar
            pygame.draw.rect(screen, (0, 255, 0), ((screen_width / 2) - 300, 30, 600, 20))
            missing_health_x = (screen_width / 2) + 300 - ((100 - spectate_player.health) / 100) * 600
            pygame.draw.rect(screen, (255, 0, 0), (missing_health_x, 30, ((100 - spectate_player.health) / 100) * 600, 20))
            pygame.draw.rect(screen, (0, 0, 0), ((screen_width / 2) - 300, 30, 600, 20), 5)
            main_clock.tick(60)
            pygame.display.update()


def run_winner_game(winner, config):

    global screen
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # clock for game
    main_clock = pygame.time.Clock()

    # map
    game_map = GameMap()

    # players
    possible_spawn_locations = get_spawn_locations()

    net = neat.nn.FeedForwardNetwork.create(winner, config)
    player = Player(possible_spawn_locations[0][0] * full_screen_tile_length, possible_spawn_locations[0][1] * full_screen_tile_length)

    # player to spectate if human is dead/not playing
    spectate_player = player

    # list of projectiles
    projectile_list = []

    # get camera dimensions from outer scope
    global camera_width
    global camera_height

    game_is_active = True
    game_ticks = 0

    while game_is_active:
        game_ticks += 1
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[K_ESCAPE]:
            pygame.quit()
            sys.exit()
        if keys[K_MINUS]:
            camera_width = camera_width * 1.02
            camera_height = camera_height * 1.02
        if keys[K_EQUALS]:
            camera_width = camera_width * 0.98
            camera_height = camera_height * 0.98

        # find what square player is on
        square_row = int(truncate(player.y / full_screen_tile_length, 0).strip("."))
        square_col = int(truncate(player.x / full_screen_tile_length, 0).strip("."))

        # find displacement
        x_displacement = player.x - square_col * full_screen_tile_length
        y_displacement = player.y - square_row * full_screen_tile_length

        # find squares
        squares = []
        row = square_row - 1
        while row <= square_row + 1:
            col = square_col - 1
            while col <= square_col + 1:
                if 0 <= row < map_num_rows and 0 <= col < map_num_cols:
                    squares.append(game_map.game_map_array[row][col])
                else:
                    squares.append(EMPTY)
                col += 1
            row += 1

        # health, storm increment, x location, y location
        # health = player.health
        # storm_advancement = game_map.storm_advancement
        x_location = player.x
        y_location = player.y
        input_list = [x_location, y_location, x_displacement, y_displacement] + squares
        # input_list.append(squares)
        # input_list.append(x_displacement)
        # input_list.append(y_displacement)
        # input_list.append(health)

        output = net.activate(tuple(input_list))

        # output 0: decide to (go up or down) or (not move)
        # output 1: decide to (go up) or (go down)
        # output 2: decide to (go right or left) or (not move)
        # output 3: decide to (go right) or (go left)

        if output[0] > 0.5:
            if output[1] > 0.5:
                player.move(0, -1, game_map)
            else:
                player.move(0, 1, game_map)

        if output[2] > 0.5:
            if output[3] > 0.5:
                player.move(1, 0, game_map)
            else:
                player.move(-1, 0, game_map)

        # update everything

        if game_ticks % game_map.storm_rate == 0:
            game_map.storm_advancement += 1

        player.update(game_map)
        # fitness based on how long players survive
        # ge[n].fitness += 1
        if player.health <= 0:
           pygame.quit()
           break

        for n, projectile in enumerate(projectile_list):
           projectile.update(game_map)
           if projectile.is_gone:
               projectile_list.pop(n)

        # draw everything
        game_map.draw(spectate_player.x, spectate_player.y)
        player.draw(spectate_player.x, spectate_player.y)
        for projectile in projectile_list:
            projectile.draw(spectate_player.x, spectate_player.y)
        # labels
        pygame.draw.rect(screen, (0, 0, 0), (1180, 80, 200, 180))
        fps = main_clock.get_fps()
        my_font = pygame.font.SysFont("monospace", 50)
        fps_label = my_font.render("fps: " + str(round(fps)), 1, (0, 0, 255))
        screen.blit(fps_label, (1200, 100))
        num_kills_label = my_font.render("kills: " + str(spectate_player.num_kills), 1, (0, 0, 255))
        screen.blit(num_kills_label, (1200, 150))
        ammo_label = my_font.render("ammo: " + str(spectate_player.ammunition), 1, (0, 0, 255))
        screen.blit(ammo_label, (1200, 200))
        # health bar
        pygame.draw.rect(screen, (0, 255, 0), ((screen_width / 2) - 300, 30, 600, 20))
        missing_health_x = (screen_width / 2) + 300 - ((100 - spectate_player.health) / 100) * 600
        pygame.draw.rect(screen, (255, 0, 0),
                         (missing_health_x, 30, ((100 - spectate_player.health) / 100) * 600, 20))
        pygame.draw.rect(screen, (0, 0, 0), ((screen_width / 2) - 300, 30, 600, 20), 5)
        main_clock.tick(60)
        pygame.display.update()


def run(config_path):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_path)
    p = neat.Population(config)

    # Add a stdout reporter to show progress in the terminal.
    p.add_reporter(neat.StdOutReporter(True))
    p.add_reporter(neat.StatisticsReporter())

    # Run for up to 50 generations.
    winner = p.run(get_player_fitness_a_star, 10000)

    # show final stats
    print('\nBest genome:\n{!s}'.format(winner))

    run_winner_game(winner, config)

    fig = plt.figure()
    fig.subplots_adjust(top=0.95)
    ax1 = fig.add_subplot(1, 1, 1)
    ax1.set_ylabel('fitness')
    ax1.set_xlabel('generations')
    ax1.set_title('fitness of best genome vs current generation')
    ax1.plot(best_fitness)
    plt.show()


if __name__ == "__main__":
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, "config-feedforward.txt")
    run(config_path)
