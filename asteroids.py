#!/usr/bin/env python3
# Asteroids
#
# by Brett and David Smith
# 12/14/2018

import math
import pygame as pg
import pygame.display as pgd
import random
import time

#from spaceobjects import *
from spaceobjects.Spaceobjects import *

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GAMESPEED_FPS = 30

LEVEL_WIDTH = 4*SCREEN_WIDTH
LEVEL_HEIGHT = 3*SCREEN_HEIGHT

CAMERA_X_DECEL_DIST = SCREEN_WIDTH // 4
CAMERA_Y_DECEL_DIST = SCREEN_HEIGHT // 4

SHIP_START_LOCATION = (LEVEL_WIDTH//2, LEVEL_HEIGHT//2)

ASTEROID_STARTING_COUNT = 10

DRAW_LEVEL_BORDER = True        # Show border around the level
HUDMAP_SCALING_FACTOR = 0.05

GAME_FONT = "unispacebold"

SCORE_ASTEROID_HIT = 10


class Viewport:


    class Camera:
        UPDATETYPE_SIMPLE = "simple"
        UPDATETYPE_SMOOTH_EXP = "smooth_exp"


        def __init__(self, display_width, display_height, level_width, level_height, cam_x=0, cam_y=0):
            self.display_width = display_width
            self.display_height = display_height
            self.level_width = level_width
            self.level_height = level_height
            self.x = cam_x
            self.y = cam_y

            # Stores camera tracking limit coords
            self.cam_limit = {"left": self.display_width//2, "right": self.level_width - self.display_width//2, "top": self.display_height//2, "bottom": self.level_height - self.display_height//2}


        def apply(self, x, y):
            """
            Apply the camera translation to the x,y world coordinate and return the translated coords at which to
            display object.
            :param x: Object's world x coordinate.
            :param y: Object's world y coordinate.
            :return: Object's camera display coordinates. (Translated by the camera from world coordinates.)
            """
            # Convert cam's center coords to upper left coord
            cam_left_corner = self.x - self.display_width // 2
            cam_top_corner = self.y - self.display_height // 2

            # Translate x,y by cam coords
            return (x - cam_left_corner, y - cam_top_corner)


        def update(self, type_string, new_x, new_y, *args):
            """
            Attempt to update the camera center x and y coordinate while respecting camera hard-limits.
            :param type_string: String indicating type of update algorithm desired.
            :param new_x: Next desired x position for camera center.
            :param new_y: Next desired y position for camera center.
            :return: None
            """
            if type_string.lower() == self.UPDATETYPE_SIMPLE:
                self._abrupt_update(new_x, new_y)
            elif type_string.lower() == self.UPDATETYPE_SMOOTH_EXP:
                self._smooth_update(new_x, new_y, *args)
            else:
                raise NotImplementedError("Invalid update type specified.")


        def _abrupt_update(self, new_x, new_y):
            """
            Handle camera update using an abrupt stop when reaching camera position hard-limits.
            :param new_x: Next desired x position for camera center.
            :param new_y: Next desired y position for camera center.
            :return: None
            """
            camtracklimit_right = self.level_width - self.display_width//2
            camtracklimit_left = self.display_width//2
            camtracklimit_top = self.display_height//2
            camtracklimit_bottom = self.level_height - self.display_height//2

            # Allow camera tracking until 1/2 screen width/height from edge
            self.x = min(max(new_x, camtracklimit_left), camtracklimit_right)
            self.y = min(max(new_y, camtracklimit_top), camtracklimit_bottom)


        def _smooth_update(self, new_x, new_y, cam_x_decel_distance=None, cam_y_decel_distance=None):
            """
            Handle camera update using a smoothed deceleration when approaching camera position hard-limits.
            :param new_x: Next desired x position for camera center.
            :param new_y: Next desired y position for camera center.
            :return: None
            """

            # If not specified, choose default decel distances
            if cam_x_decel_distance is None:
                cam_x_decel_distance = self.display_width // 4
            if cam_y_decel_distance is None:
                cam_y_decel_distance = self.display_height // 4

            def cam_decel_and_limit(cam_begin_decel_coord, cam_limit_coord, tracking_coord):
                """
                Function computes a natural exponential decel curve for the camera relative to the tracked object's
                coordinate when it is between the beginning of the cameral decel coord and the camera hard limit.
                :param cam_begin_decel_coord: The x or y coordinate at which to begin decelerating the camera.
                :param cam_limit_coord: The x or y coordinate at which the camera is hard-limited from passing.
                :param tracking_coord: The coordinate of the object that the camera is tracking.
                :return: The calculated offset of the camera from the camera hard limit.
                """
                cam_decel_distance = abs(cam_begin_decel_coord - cam_limit_coord)   # Distance over which cam decels
                tau = cam_decel_distance // 2                                       # Exponential decay "time constant"
                                                                                    # (A smaller tau results in more abrupt stop)
                x = abs(tracking_coord - cam_begin_decel_coord)                     # How far the cam is into decel zone
                decay = math.exp(-x/tau)                                            # Exponential decay
                return decay * cam_decel_distance

            # Calc temp camera x coord - it follows the tracked object in cam-locked manner (between decel points)
            tx = min(max(new_x, self.cam_limit["left"] + cam_x_decel_distance), self.cam_limit["right"] - cam_x_decel_distance)

            # Determine camera behaviour (cam-locked full speed tracking or decel and stop)
            if tx == new_x:
                # In full-speed camera tracking zone (cam-locked)
                self.x = tx
            else:
                # Camera tracking is decelerating or hard-limited by camera stop
                # Handle left camera boundary
                cam_limit_coord = self.cam_limit["left"]
                cam_begin_decel_coord = cam_limit_coord + cam_x_decel_distance
                if new_x < cam_begin_decel_coord:
                    scaled_x = cam_limit_coord + cam_decel_and_limit(cam_begin_decel_coord, cam_limit_coord, new_x)
                    self.x = max(new_x, scaled_x)

                # Handle right camera boundary
                cam_limit_coord = self.cam_limit["right"]
                cam_begin_decel_coord = cam_limit_coord - cam_x_decel_distance
                if new_x > cam_begin_decel_coord:
                    scaled_x = cam_limit_coord - cam_decel_and_limit(cam_begin_decel_coord, cam_limit_coord, new_x)
                    self.x = min(new_x, scaled_x)

            # Calc temp camera y coord - it follows the tracked object in cam-locked manner (between decel points)
            ty = min(max(new_y, self.cam_limit["top"] + cam_y_decel_distance), self.cam_limit["bottom"] - cam_y_decel_distance)

            # Determine camera behaviour (cam-locked full speed tracking or decel and stop)
            if ty == new_y:
                # In full-speed camera tracking zone (cam-locked)
                self.y = ty
            else:
                # Handle top camera boundary
                cam_limit_coord = self.cam_limit["top"]
                cam_begin_decel_coord = cam_limit_coord + cam_y_decel_distance
                if new_y < cam_begin_decel_coord:
                    scaled_y = cam_limit_coord + cam_decel_and_limit(cam_begin_decel_coord, cam_limit_coord, new_y)
                    self.y = max(new_y, scaled_y)

                # Handle bottom camera boundary
                cam_limit_coord = self.cam_limit["bottom"]
                cam_begin_decel_coord = cam_limit_coord - cam_y_decel_distance
                if new_y > cam_begin_decel_coord:
                    scaled_y = cam_limit_coord - cam_decel_and_limit(cam_begin_decel_coord, cam_limit_coord, new_y)
                    self.y = min(new_y, scaled_y)


    def __init__(self, viewport_width, viewport_height, level_width=None, level_height=None):
        self.width = viewport_width
        self.height = viewport_height
        self.level_width = level_width if level_width is not None else viewport_width
        self.level_height = level_height if level_height is not None else viewport_height

        # Create main pygame display
        self.display = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        # Start with no camera
        self.camera = None


    def create_camera(self, cam_x, cam_y):
        self.camera = Viewport.Camera(self.width, self.height, self.level_width, self.level_height, cam_x, cam_y)



    def render(self, sprite: pg.Surface, x, y):
        if sprite is None:
            return

        # Calc upper left coord of sprite
        x_temp = x - Viewport._half_w(sprite)
        y_temp = y - Viewport._half_h(sprite)

        if self.camera is None:
            self.display.blit(sprite, (x_temp, y_temp))
        else:
            translated_to_cam_x, translated_to_cam_y = self.camera.apply(x_temp, y_temp)
            self.display.blit(sprite, (translated_to_cam_x, translated_to_cam_y))


    @staticmethod
    def _half_w(sprite: pg.Surface):
        return sprite.get_rect().w//2


    @staticmethod
    def _half_h(sprite: pg.Surface):
        return sprite.get_rect().h//2



class GameData:
    high_score = 0

    def __init__(self):
        self.score = 0
        self.level = 1
        self.lives = 3
        self.respawn_timestamp = 0
        self.is_gameover = False

        self.is_levelup_delay = False
        self.levelup_delay_timestamp = 0

    def reset(self):
        self.__init__()



def render_map(map_surface, ship, asteroids_list, scaling_factor=0.1, transparent_background=True):
    def scale_xy(x, y, scaling_factor):
        x = int(x * scaling_factor)
        y = int(y * scaling_factor)
        return x, y

    # Map surface width and height
    w = map_surface.get_rect().width
    h = map_surface.get_rect().height

    if transparent_background:
        # 'screen' configured to make "black" transparent background
        map_surface.fill(colormap["black"])
    else:
        # 'screen' translates "black" to transparent, so make fill "almost" black to keep it from being made transparent
        map_surface.fill((1, 1, 1))

    # Draw map border
    pg.draw.rect(map_surface, colormap["blue"], (0, 0, w, h), 1)

    # "Overlay" a pixel array on the surface to allow x,y access to pixels
    map_pa = pg.PixelArray(map_surface)

    # Ship position
    x, y = scale_xy(ship.coord_x, ship.coord_y, scaling_factor)
    if (x >= 0 and x < w) and (y >= 0 and y < h) and ship.is_alive:
        map_pa[x, y] = colormap["red"]

    # Asteroid positions
    for rock in asteroids_list:
        x, y = scale_xy(rock.coord_x, rock.coord_y, scaling_factor)
        if (x >= 0 and x < w) and (y >= 0 and y < h):
            map_pa[x, y] = colormap["white"]
        else:
            continue

    map_pa.close()
    return


def choose_font(fonts, size):
    available = pg.font.get_fonts()
    # get_fonts() returns a list of lowercase spaceless font names
    choices = map(lambda x:x.lower().replace(' ', ''), fonts)

    for choice in choices:
        if choice in available:
            return pg.font.SysFont(choice, size)
    return pg.font.Font(None, size)



def render_hud(hud_surface, map_surface, ship, asteroids, game_data):
    a, b, w, h = hud_surface.get_rect()


    # Update the map
    render_map(map_surface, ship, asteroids, HUDMAP_SCALING_FACTOR, transparent_background=True)

    #### WORKING HERE
    # ** MUST IMPROVE BY MOVING SOME OF THIS OUT SO IT DOESN't GET COMPUTED EVERY TIME**
    # Display score
    # Fonts that look good: unispacebold, impact, couriernew,
    HUD_SCORE_LOCATION = (int(w*.85), 5)
    gamefont = choose_font(GAME_FONT, 24)
    score_txt = gamefont.render("Score: " + str(game_data.score), False, colormap["white"])
    highscore_txt = gamefont.render("High Score: " + str(GameData.high_score), False, colormap["white"])

    hud_surface.fill(colormap["black"])                     # "Erase" hud before writing
    hud_surface.blit(score_txt, HUD_SCORE_LOCATION)
    HUD_HIGHSCORE_LOCATION = (int((w-highscore_txt.get_rect().width)/2), 5)
    hud_surface.blit(highscore_txt, HUD_HIGHSCORE_LOCATION)

    # Display lives remaining
    HUD_LIVES_LOCATION = (int(w*.05), 5)
    lives_txt = gamefont.render("Lives: ", False, colormap["white"])
    lives_txt_width = lives_txt.get_rect().width
    hud_surface.blit(lives_txt, HUD_LIVES_LOCATION)
    ship_display = Ship(0, 0, 0, 0)
    ship_image = ship_display.render()
    for i in range(game_data.lives):
        ship_x_offset = i * (ship_image.get_rect().width + 2)
        hud_surface.blit(ship_image, ((lives_txt_width + 10 + HUD_LIVES_LOCATION[0]) + ship_x_offset, 5))


    ################

    # Draw HUD:
    hud_surface.blit(map_surface, (
    SCREEN_WIDTH - LEVEL_WIDTH * HUDMAP_SCALING_FACTOR - 5, SCREEN_HEIGHT - LEVEL_HEIGHT * HUDMAP_SCALING_FACTOR - 5))


def create_asteroids(number):
    _asteroids = []

    for i in range(number):
        a = Asteroid(random.randint(0, LEVEL_WIDTH), random.randint(0, LEVEL_HEIGHT), random.randint(-5, 5), random.randint(-5, 5))
        a.set_move_bounds(LEVEL_WIDTH, LEVEL_HEIGHT, edge_bounce=False)
        a.rotate(random.randint(0, 360))
        a.select_size(random.randint(0, Asteroid.MAX_SIZE))
        _asteroids.append(a)
    return _asteroids


def init_game():
    global gamedata, screen, viewport, hud_surface, map_surface

    # Initialize pygame
    pg.init()


    # Globals
    gamedata = GameData()

    # Create viewport to control display
    viewport = Viewport(SCREEN_WIDTH, SCREEN_HEIGHT, LEVEL_WIDTH, LEVEL_HEIGHT)
    viewport.create_camera(LEVEL_WIDTH//2, LEVEL_HEIGHT//2)
    screen = viewport.display

    # Create a HUD overlay
    hud_surface = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    hud_surface.set_colorkey(colormap["black"])

    map_surface = pg.Surface((LEVEL_WIDTH*HUDMAP_SCALING_FACTOR, LEVEL_HEIGHT*HUDMAP_SCALING_FACTOR))


def game_loop():

    clock = pg.time.Clock()

    weapons = []
    dead_objects = []
    asteroids = create_asteroids(ASTEROID_STARTING_COUNT)

    ship = Ship(SHIP_START_LOCATION[0], SHIP_START_LOCATION[1], 0, 0)
    ship.set_move_bounds(LEVEL_WIDTH, LEVEL_HEIGHT, edge_bounce=True)


    is_done = False
    while not is_done:
        # Check for pygame events
        for event in pg.event.get():
            if event.type == pg.QUIT:
                is_done = True

            # Event-based key handling
            # If key pressed, take action
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    # Shoot plasma
                    weapon = ship.shoot("plasma")
                    if weapon:
                        weapon.set_move_bounds(edge_bounce=False)
                        weapon.animation_config(.05)
                        weapon.animation_start()
                        weapons.append(weapon)
                elif event.key == pg.K_d:
                    # Shoot deathblossom
                    ship.shoot("deathblossom")

                elif gamedata.is_gameover and (event.key == pg.K_RETURN):
                    # Record session high score
                    if gamedata.score > GameData.high_score:
                        GameData.high_score = gamedata.score

                    # Reset state and restart game
                    gamedata.reset()
                    return True

        # Handle key press with key repeat
        key = pg.key.get_pressed()
        if key[pg.K_LEFT] and not key[pg.K_RIGHT]:
            ship.rotate(6)
        elif key[pg.K_RIGHT] and not key[pg.K_LEFT]:
            ship.rotate(-6)
        if key[pg.K_LSHIFT]:
            ship.thrust(.5)



        # Erase screen
        screen.fill(colormap["black"])


        # Draw border for level
        if DRAW_LEVEL_BORDER:
            screen_rect = pg.Rect(0, 0, LEVEL_WIDTH, LEVEL_HEIGHT)
            screen_rect.x = -(viewport.camera.x - SCREEN_WIDTH//2)
            screen_rect.y = -(viewport.camera.y - SCREEN_HEIGHT//2)
            pg.draw.rect(screen, colormap["red"], screen_rect, 8)


        # Handle asteroids
        for rock in asteroids:
            rock.update()

            # Check and handle weapon hit
            for weapon in weapons:
                if weapon.is_collision(rock):
                    gamedata.score += SCORE_ASTEROID_HIT
                    rock.is_alive = False
                    weapon.is_alive = False

                    # Add to list to be deleted
                    dead_objects.append(rock)
                    dead_objects.append(weapon)

                    # Break asteroid into smaller ones
                    if rock.size > 0:
                        for i in range(Asteroid.MAX_SIZE - rock.size + 2):
                            # NEED TO PICK NEW COORDS BETTER
                            a = Asteroid(rock.coord_x - 20 + i*10, rock.coord_y - 20 + i*10, random.randint(-5, 5), random.randint(-5, 5))
                            a.select_size(rock.size-1)
                            a.set_move_bounds(LEVEL_WIDTH, LEVEL_HEIGHT, edge_bounce=False)
                            a.rotate(random.randint(0, 360))
                            asteroids.append(a)

                    # If one weapon destroys the asteroid, don't allow others to hit
                    break

            # Check and handle deathblossom hit
            if ship.is_firing_deathblossom and (rock.distance_to(ship) <= ship.deathblossom_radius + min(rock.sprite_width // 2, rock.sprite_height // 2)):
                gamedata.score += SCORE_ASTEROID_HIT
                rock.is_alive = False

                # Add to list to be deleted
                dead_objects.append(rock)


            # # Check for collisions
            # for other in asteroids:
            #     if other != rock and other.is_collide(rock):
            #        other.make_bounce(rock)

            # Test for collision with ship
            if rock.is_collision(ship):
                ship.animation_config(ship.ANIMATION_BOOM_FRAME_TIME, "boom", False)
                ship.animation_start()
                ship.is_alive = False

                RESPAWN_DELAY_SECS = 4
                gamedata.respawn_timestamp = time.time() + RESPAWN_DELAY_SECS


        # Update weapon positions
        for weapon in weapons:
            weapon.update()
            if not weapon.is_alive:
                dead_objects.append(weapon)


        # Cleanup lists - remove "dead" objects
        for dead_object in dead_objects:
            try:
                if isinstance(dead_object, Asteroid):
                    asteroids.remove(dead_object)
                elif isinstance(dead_object, Plasma_weapon):
                    weapons.remove(dead_object)

            except ValueError:
                pass
        dead_objects = []

        # Draw asteroids
        for rock in asteroids:
            if rock.is_alive:
                viewport.render(rock.render(), rock.coord_x, rock.coord_y)

        # Draw weapons
        for weapon in weapons:
            viewport.render(weapon.render(), weapon.coord_x, weapon.coord_y)

        # Update ship and camera
        ship.update()
        if ship.is_alive or (not ship.is_alive and ship.animation_complete is False):
            viewport.camera.update(Viewport.Camera.UPDATETYPE_SMOOTH_EXP, ship.coord_x, ship.coord_y,
                                   CAMERA_X_DECEL_DIST, CAMERA_X_DECEL_DIST)
        else:
            # Respawn if more lives
            if gamedata.lives > 0:
                if time.time() > gamedata.respawn_timestamp:
                    ship = Ship(SHIP_START_LOCATION[0], SHIP_START_LOCATION[1], 0, 0)
                    ship.set_move_bounds(LEVEL_WIDTH, LEVEL_HEIGHT, edge_bounce=True)
                    gamedata.lives -= 1
            else:
                # Game over
                gamedata.is_gameover = True

                # Update high score
                if gamedata.score > GameData.high_score:
                    GameData.high_score = gamedata.score

                gameover_font = choose_font(GAME_FONT, 50)
                gameover_txt = gameover_font.render("GAME OVER", False, colormap["white"])
                screen.blit(gameover_txt, ((SCREEN_WIDTH - gameover_txt.get_rect().width)/2, (SCREEN_HEIGHT - gameover_txt.get_rect().height)/2))

                restart_font = choose_font(GAME_FONT, 25)
                restart_txt = restart_font.render("(Press 'Enter' to Play Again)", False, colormap["white"])
                screen.blit(restart_txt, ((SCREEN_WIDTH - restart_txt.get_rect().width)/2, (SCREEN_HEIGHT + gameover_txt.get_rect().height + 12 - restart_txt.get_rect().height)/2))

        # Detect when all asteroids destroyed and increase level
        if not asteroids:
            if not gamedata.is_levelup_delay:
                # Increase level and get extra life
                gamedata.level += 1
                if gamedata.lives < 5:
                    gamedata.lives += 1

                LEVELUP_DELAY_SECS = 4
                gamedata.is_levelup_delay = True
                gamedata.levelup_delay_timestamp = time.time() + LEVELUP_DELAY_SECS
            else:
                if time.time() > gamedata.levelup_delay_timestamp:
                    # Spawn more asteroids
                    asteroids = create_asteroids(ASTEROID_STARTING_COUNT + (gamedata.level - 1)*5)
                    gamedata.is_levelup_delay = False

        # Draw ship
        viewport.render(ship.render(), ship.coord_x, ship.coord_y)

        # Draw HUD:
        render_hud(hud_surface, map_surface, ship, asteroids, gamedata)
        screen.blit(hud_surface, (0, 0))

        # Make newly drawn things visible
        pg.display.flip()
        clock.tick(GAMESPEED_FPS)

    return False



def main():
    init_game()

    startgame = True
    while startgame:
        startgame = game_loop()


# MAIN ENTRY POINT
main()
exit(0)