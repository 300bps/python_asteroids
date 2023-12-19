import itertools
import math
import pygame as pg
import random
import os
import sys
import time

# DEBUG OPTIONS
DEBUG_SHOW_HITBOX = False


colormap = {"white": (255, 255, 255), "black": (0, 0, 0), "red": (255, 0, 0), "blue": (0, 0, 255),
            "yellow": pg.color.THECOLORS["yellow"], "green": pg.color.THECOLORS["green"], "orange": pg.color.THECOLORS["orange"]}


class Spaceobject:
    """
    Base class for space objects.
    """
    DEFAULTSIZE_WIDTH = 28
    DEFAULTSIZE_HEIGHT = 28


    def __init__(self, coord_x, coord_y, speed_x=0, speed_y=0, heading=0):
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.speed_x = speed_x
        self.speed_y = speed_y
        self.heading = heading

        # Make the sprites for the various images of this object
        self.sprite_list = self._create_sprites()

        # Define structures used for animation and animation sequences
        self.is_animating = False
        self.animation_complete = False
        self.animate_frame_display_time_secs = 0
        self.animate_timestamp = 0
        self.animation_list_index_iter = None
        self.animation_sequences_dict = self._create_animation_sequences(self.sprite_list)

        # Create variables to hold the master (untransformed) and working sprite (possibly transformed)
        self.sprite_master = None
        self.sprite = None

        # Select initial sprite and assign it to self.sprite_master and self.sprite
        self.switch_sprite(0, True)
        (a, b, self.sprite_width, self.sprite_height) = self.sprite.get_rect()

        # Value that can be used to reduce the size of the object's hitbox by a number of pixels to allow some
        # overlap before collision will be reported as True.  Should be an even number so 1/2 can be removed from each
        # side of the center of the sprite.
        self.shrinkhitbox_xy = 0

        # Define bounds settings and set defaults
        self.bounds_leftx = 0
        self.bounds_rightx = 0
        self.bounds_topy = 0
        self.bounds_bottomy = 0
        self.bounds_edgebounce = False
        self.set_move_bounds()

        # Define and set properties
        self.is_alive = False
        self.is_solid = False
        self.is_visible = False
        self.set_properties()


    def set_move_bounds(self, width=10000, height=10000, leftx=0, topy=0, edge_bounce=False):
        """
        Set world boundaries for object.
        :param width:
        :param height:
        :param leftx:
        :param topy:
        :param edge_bounce:
        :return:
        """
        self.bounds_leftx = leftx
        self.bounds_rightx = leftx + width
        self.bounds_topy = topy
        self.bounds_bottomy = topy + height
        self.bounds_edgebounce = edge_bounce


    def set_properties(self, is_alive=True, is_solid=True, is_visible=True, alpha_color_str=None):
        self.is_alive = is_alive
        self.is_solid = is_solid
        self.is_visible = is_visible

        # Set alpha background color for transparent color
        alpha_color = colormap.get(alpha_color_str, None)
        if alpha_color_str and alpha_color:
            # Update all sprites in the list
            for sp in self.sprite_list:
                if sp:
                    sp.set_colorkey(alpha_color)

            # Update working sprite
            if self.sprite:
                self.sprite.set_colorkey(alpha_color)


    def _create_sprites(self):
        """
        Subclasses override this function to create the sprites for the subclass.
        :return: A list containing pygame.Surface objects of the various sprites for this object.
        """

        # Create or load sprites
        sp = pg.Surface((self.DEFAULTSIZE_WIDTH, self.DEFAULTSIZE_HEIGHT))
        sp.set_colorkey(colormap.get(colormap["black"]))

        # Create dummy sprite
        pg.draw.rect(sp, colormap["white"], pg.Rect(0, 0, self.DEFAULTSIZE_WIDTH, self.DEFAULTSIZE_HEIGHT), 0)
        sprite_list = [sp]

        return sprite_list


    def _create_animation_sequences(self, sprite_list):
        """
        Subclasses override this function to create the animation sequences for the subclass.
        :param sprite_list: List of sprites defined for this object.
        :return:
        """
        animation_seq_dict = {}
        animation_seq_dict["all"] = list(range(len(sprite_list)))
        animation_seq_dict["reversed"] = list(reversed(list(range(len(sprite_list)))))

        return animation_seq_dict


    def switch_sprite(self, sprite_index, apply_heading_rotation=True):
        """
        Switch to a new sprite in the sprite list.
        :param sprite_index: Index of the sprite to which to switch.
        :param apply_heading_rotation: True/False - Rotate the working sprite to object's current heading.
        :return: None
        """
        try:
            self.sprite_master = self.sprite_list[sprite_index]
            self.sprite = self.sprite_master.copy()
            if apply_heading_rotation:
                self.rotate(0)

            # Update sprite dimensions
            (a, b, self.sprite_width, self.sprite_height) = self.sprite.get_rect()

        except IndexError:
            pass


    def rotate(self, degrees):
        """
        Rotate the object.
        :param degrees: Number of degrees to rotate.  '+' is counter-clockwise; '-' is clockwise
        :return: None
        """
        # Update heading
        self.heading += degrees
        if self.heading > 360:
            self.heading -= 360
        elif self.heading < -360:
            self.heading += 360

        # Rotate a copy of the original unrotated sprite to reduce image flaws
        unrotated_sprite = self.sprite_master
        new_sprite = pg.transform.rotate(unrotated_sprite, self.heading)

        # Update sprite dimensions
        (a, b, self.sprite_width, self.sprite_height) = new_sprite.get_rect()

        # Make the new sprite the current working sprite
        self.sprite = new_sprite


    def update(self):
        """
        Update object's state (position, etc.)
        :return: None
        """
        # Update item position
        self._update_position()


    def _update_position(self):
        """
        Update object's position with respect to bounds checking.
        :return: None
        """
        cx = self.coord_x
        cy = self.coord_y

        # Calculate next position
        cx += self.speed_x
        cy += self.speed_y

        # Bounds checking x
        if cx > self.bounds_rightx:
            if self.bounds_edgebounce:
                self.speed_x = -self.speed_x
                cx = self.bounds_rightx
            else:
                cx = self.bounds_leftx

        elif cx < self.bounds_leftx:
            if self.bounds_edgebounce:
                self.speed_x = -self.speed_x
                cx = self.bounds_leftx
            else:
                cx = self.bounds_rightx

        # Bounds checking y
        if cy > self.bounds_bottomy:
            if self.bounds_edgebounce:
                self.speed_y = -self.speed_y
                cy = self.bounds_bottomy
            else:
                cy = self.bounds_topy

        elif cy < self.bounds_topy:
            if self.bounds_edgebounce:
                self.speed_y = -self.speed_y
                cy = self.bounds_topy
            else:
                cy = self.bounds_bottomy

        # Update official position
        self.coord_x = cx
        self.coord_y = cy


    def is_collision(self, other):
        """
        Test for collision.
        :param other: Other entity of the same base type to test.
        :return: True or False
        """
        # If not solid, visible, or alive, don't check collisions
        if not self.is_solid or not self.is_visible or not self.is_alive:
            return

        if not other.is_solid or not other.is_visible or not other.is_alive:
            return

        my_halfx = int((self.sprite_width-self.shrinkhitbox_xy)/2)
        my_halfy = int((self.sprite_height-self.shrinkhitbox_xy)/2)
        other_halfx = int((other.sprite_width-other.shrinkhitbox_xy)/2)
        other_halfy = int((other.sprite_height-other.shrinkhitbox_xy)/2)

        # Location of my right corner and left corner
        rx = self.coord_x + my_halfx
        lx = self.coord_x - my_halfx
        if (rx < other.coord_x - other_halfx) or (lx > other.coord_x + other_halfx):
            overlap_x = False
        else:
            overlap_x = True


        # Location of my top corner and bottom corner
        by = self.coord_y + my_halfy
        ty = self.coord_y - my_halfy
        if (by < other.coord_y - other_halfy) or (ty > other.coord_y + other_halfy):
            overlap_y = False
        else:
            overlap_y = True

        if overlap_x and overlap_y:
            return True

        return False


    def make_bounce(self, other):
        """
        Make this object bounce off of 'other'.
        :param other: Other entity of the same type.
        :return: None
        """
        # If not solid, visible, or alive, then it doesn't bounce
        if not self.is_solid or not self.is_visible or not self.is_alive:
            return

        # TODO: This algorithm needs improvement
        if self.is_collision(other):
            # self.speed_x = -self.speed_x
            # self.speed_y = -self.speed_y
            self.speed_x = -self.speed_x if other.speed_x*self.speed_x < 0 else self.speed_x
            self.speed_y = -self.speed_y if other.speed_y*self.speed_y < 0 else self.speed_y

            # Move to outside of bounce boundary
            loopcount = 0
            while self.is_collision(other) and loopcount < 3:
                self._update_position()
                loopcount += 1


    def distance_to(self, other=None, coordinate=(None, None)):
        """
        Calculate the distance to the "other" object or the specified coordinate.
        :param other: The object to which to calculate the distance.
        :return: Floating point distance to the other object.
        """
        if other and isinstance(other, Spaceobject):
            x = other.coord_x
            y = other.coord_y
        # elif x_coord is not None and y_coord is not None:
        elif coordinate[0] is not None and coordinate[1] is not None:
            x = coordinate[0]
            y = coordinate[1]
        else:
            raise ValueError("Must pass either a valid object or an (x,y) coordinate tuple.")

        delx = x - self.coord_x
        dely = y - self.coord_y
        return math.sqrt(delx*delx + dely*dely)


    def render(self) -> pg.Surface:
        """
        Return the sprite to be rendered.
        :return: Sprite to render
        """
        # If not visible or alive, don't draw
        if not self.is_visible or not self.is_alive:
            return None

        # Current sprite
        sprite = self.sprite

        # If animated, handle animation sequence
        if self.is_animating:
            sprite = self._animate()

        # Show hitbox for debugging
        if "DEBUG_SHOW_HITBOX" in globals() and DEBUG_SHOW_HITBOX:
            _, _, w, h = sprite.get_rect()
            pg.draw.rect(sprite, colormap["red"], (int(self.shrinkhitbox_xy/2), int(self.shrinkhitbox_xy/2), w-self.shrinkhitbox_xy, h-self.shrinkhitbox_xy), 1)

        return sprite


    def animation_config(self, frame_display_time_secs=0.1, animation_sequence_name="", animation_repeat=True):
        self.animate_frame_display_time_secs = frame_display_time_secs
        self.animate_timestamp = 0

        # Pick type of iterator to use based on whether animation repeats or not.
        if animation_repeat:
            iter_to_use = itertools.cycle
        else:
            iter_to_use = iter

        # Choose animation sequence to use
        if animation_sequence_name:
            animation_seq = self.animation_sequences_dict.get(animation_sequence_name, None)
            if animation_seq is None:
                raise KeyError("Animation sequence name not found.")
        else:
            animation_seq = range(len(self.sprite_list))

        self.animation_list_index_iter = iter_to_use(animation_seq)


    def animation_start(self):
        # If animation hasn't been explicitly configured, configure it with defaults.
        if self.animation_list_index_iter is None:
            self.animation_config()

        self.is_animating = True


    def animation_stop(self):
        self.is_animating = False


    def _animate(self):
        if time.time() >= self.animate_timestamp:
            # If not first displayed frame, switch to next sprite in animation sequence
            if self.animate_timestamp != 0:
                try:
                    index = next(self.animation_list_index_iter)
                    self.switch_sprite(index, True)

                except StopIteration:
                    self.animation_complete = True
                    self.is_animating = False

            # Set next animation frame timestamp
            self.animate_timestamp = time.time() + self.animate_frame_display_time_secs

        return self.sprite



class Asteroid(Spaceobject):
    MAX_SIZE = 2
    MAX_SPIN_SPEED = 1.5

    size = MAX_SIZE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create random spin
        self.spin = self.MAX_SPIN_SPEED * random.random() * random.choice([-1, 1])


    def select_size(self, size=MAX_SIZE):
        """
        Select asteroid size.
        :param size: Value from MAX_SIZE down to 0 with size directly proportional to number.
        :return: None
        """
        if size > self.MAX_SIZE or size > len(self.sprite_list):
            raise ValueError("Invalid size.")

        self.size = size
        self.switch_sprite(size)


    def update(self):
        super().update()

        # Handle asteroid spin
        if self.spin != 0:
            self.rotate(self.spin)


    def _create_sprites(self):
        # Load images
        filename = os.path.join(sys.path[0], "asteroid0.png")
        asteroid_size0 = pg.image.load(filename)

        filename = os.path.join(sys.path[0], "asteroid1.png")
        asteroid_size1 = pg.image.load(filename)

        filename = os.path.join(sys.path[0], "asteroid2.png")
        asteroid_size2 = pg.image.load(filename)

        sprite_list = [asteroid_size0, asteroid_size1, asteroid_size2]

        # Set alpha background color for transparent color
        for each in sprite_list:
            each.set_colorkey(colormap.get(colormap["black"]))

        return sprite_list



class Plasma_weapon(Spaceobject):

    TIME_TO_LIVE_SECS = 1

    def __init__(self, coord_x, coord_y, speed_x=0, speed_y=0, heading=0):
        super().__init__(coord_x, coord_y, speed_x, speed_y, heading)
        self.life_timeout = time.time() + self.TIME_TO_LIVE_SECS


    def _create_sprites(self):
        """
        Create sprites and animation sequences.
        :return: List of sprites
        """
        plasma = pg.image.load(os.path.join(sys.path[0], "plasma.png"))
        sprite_list = [plasma]

        return sprite_list


    def _create_animation_sequences(self, sprite_list):
        # Create default animations sequences
        animation_seq_dict = super()._create_animation_sequences(sprite_list)

        return animation_seq_dict


    def update(self):
        # Update position
        super().update()

        # Check life timeout
        if time.time() >= self.life_timeout:
            self.is_alive = False



class Ship(Spaceobject):

    MAX_SPEEDX = 10
    MAX_SPEEDY = 10

    is_thrusting = False

    # List holds live missile weapons in flight
    missile_weapons = []

    WEAPON_PLASMA_SPEED = 8
    WEAPON_PLASMA_MAXLIVE = 5

    WEAPON_DEATHBLOSSOM_MAXRADIUS = 125

    ANIMATION_DEATHBLOSSOM_FRAME_TIME = 0.03
    ANIMATION_DEATHBLOSSOM_DELTARAD_PER_FRAME = 10

    ANIMATION_BOOM_FRAME_TIME = 0.05

    def __init__(self, coord_x, coord_y, speed_x=0, speed_y=0, heading=0):
        super().__init__(coord_x, coord_y, speed_x=0, speed_y=0, heading=0)

        # Shrink the hitbox "slightly" to make hitbox tighter around image
        self.shrinkhitbox_xy = 6

        self.deathblossom_charges = 10
        self.is_firing_deathblossom = False
        self.deathblossom_radius = 0


    def _create_sprites(self):
        # Create and configure surface for sprite
        # size_width = 28
        # size_height = 20
        # sp = pg.Surface((size_width, size_height))

        # Other ship styles
        # h = size_height
        # w = size_width
        # shipstyle_1 = [(0, 0), (0, h-1), (w-1, h/2-1), (0, 0)]
        # shipstyle_2 = [(0,0), (w-1, h//2-1), (0, h-1), (w//4, (h-h//3)-1), (w//4, h//3 - 1), (0, 0)]
        # shipstyle_3 = [(0,0), (w//3, 0), (w-1, h//2-1), (w//3, h-1), (0, h-1), (w//4, (h-h//3)-1), (w//4, h//3 - 1), (0, 0)]
        # shipstyle_4 = [(0,0), (w//3, 0), (w//2, h//4-1), (w-1, h//2-1), (w//2, (h-h//4)-1), (w//3, h-1), (0, h-1), (w//4, (h-h//3)-1), (w//4, h//3 - 1), (0, 0)]
        # pg.draw.polygon(sp, colormap["white"], shipstyle_4)
        # sp.set_colorkey(colormap["black"])

        # Load ship image
        ship = pg.image.load(os.path.join(sys.path[0], "ship.png"))
        a, b, w, h = ship.get_rect()

        # Resize ship image to leave space for engine thrust "flame"
        ENGINEFLAME_LENGTH = 5
        sp = pg.Surface((w+ENGINEFLAME_LENGTH, h))
        sp.blit(ship, (ENGINEFLAME_LENGTH,0))
        sp.set_colorkey(colormap["black"])

        # Make model with thrust firing
        sp_thrust = sp.copy()
        thrust_outer = [(ENGINEFLAME_LENGTH, h//3-1), (ENGINEFLAME_LENGTH, (h-h//3)-1), (0, h//2-1)]
        thrust_inner = [(ENGINEFLAME_LENGTH, h//2.5-1), (ENGINEFLAME_LENGTH, (h-h//2.5)-1), (ENGINEFLAME_LENGTH-2, h//2-1)]
        pg.draw.polygon(sp_thrust, colormap["red"], thrust_outer)
        pg.draw.polygon(sp_thrust, pg.color.THECOLORS["yellow"], thrust_inner)
        sp_thrust.set_colorkey(colormap["black"])

        sprite_list = [sp, sp_thrust]

        # Explosion - smallest
        filename = os.path.join(sys.path[0], "explosion0.png")
        explosion = pg.image.load(filename)
        sprite_list.append(explosion)

        # Explosion - medium
        filename = os.path.join(sys.path[0], "explosion1.png")
        explosion = pg.image.load(filename)
        sprite_list.append(explosion)

        # Explosion - large
        filename = os.path.join(sys.path[0], "explosion2.png")
        explosion = pg.image.load(filename)
        sprite_list.append(explosion)

        # Explosion - larger
        filename = os.path.join(sys.path[0], "explosion3.png")
        explosion = pg.image.load(filename)
        sprite_list.append(explosion)

        # Explosion - largest
        filename = os.path.join(sys.path[0], "explosion4.png")
        explosion = pg.image.load(filename)
        sprite_list.append(explosion)

        # Alpha channel - select transparent color
        # for sprite in sprite_list:
        #     sprite.set_colorkey(colormap["black"])

        return sprite_list


    def _create_animation_sequences(self, sprite_list):
        animation_seq = super()._create_animation_sequences(sprite_list)

        # Explosion sequence sprite_list indexes
        explosion_seq = [2, 3, 4, 5, 6, 5, 4, 3, 2]

        animation_seq["boom"] = explosion_seq
        animation_seq["deathblossom"] = [0]

        return animation_seq


    def update(self):
        # Update position
        super().update()

        # Update live missile weapons
        del_list = []
        for m in self.missile_weapons:
            if m:
                if not m.is_alive:
                    # Add "dead" missiles to the delete list
                    del_list.append(m)

        # Delete missiles marked for deletion
        for m in del_list:
            self.missile_weapons.remove(m)


    def thrust(self, thrust_deltaspeed):
        if not self.is_alive or self.is_firing_deathblossom:
            return None

        self.is_thrusting = True

        changex = thrust_deltaspeed * math.cos(math.radians(self.heading))
        changey = thrust_deltaspeed * math.sin(math.radians(self.heading))

        sx = self.speed_x + changex
        sy = self.speed_y - changey

        # If speeds are below the speed limit, update them
        if math.fabs(sx) < self.MAX_SPEEDX:
            self.speed_x = sx
        if math.fabs(sy) < self.MAX_SPEEDY:
            self.speed_y = sy


    def _live_missile_count(self):
        count = 0
        for m in self.missile_weapons:
            if m and m.is_alive:
                count += 1

        return count


    def shoot(self, type_string):
        """
        :return:
        """
        # Can't shoot if you're dead!
        if not self.is_alive:
            return None

        if type_string == "plasma":
            if self._live_missile_count() < self.WEAPON_PLASMA_MAXLIVE:

                # Compute speed components
                weaponspeed_x = self.speed_x + self.WEAPON_PLASMA_SPEED*math.cos(math.radians(self.heading))
                weaponspeed_y = self.speed_y - self.WEAPON_PLASMA_SPEED*math.sin(math.radians(self.heading))

                weapon = Plasma_weapon(self.coord_x, self.coord_y, weaponspeed_x, weaponspeed_y, self.heading)
                weapon.set_properties(True, True, True)
                self.missile_weapons.append(weapon)

                return weapon

        elif type_string == "deathblossom":
            if not self.is_firing_deathblossom and self.deathblossom_charges > 0:
                self.deathblossom_charges -= 1
                self.is_firing_deathblossom = True
                self.deathblossom_radius = self.sprite_width // 2

                # Config for animation
                self.animation_config(frame_display_time_secs=self.ANIMATION_DEATHBLOSSOM_FRAME_TIME, animation_sequence_name="deathblossom", animation_repeat=True)
                self.animation_start()

        else:
            raise NotImplementedError("Weapon type not implemented.")

        return None


    def _animate(self):
        time_now = time.time()
        sprite_to_display = self.sprite

        if time_now >= self.animate_timestamp:
            # If not first displayed frame, switch to next sprite in animation sequence
            if self.animate_timestamp != 0:
                try:
                    index = next(self.animation_list_index_iter)
                    self.switch_sprite(index, True)
                    sprite_to_display = self.sprite

                except StopIteration:
                    self.animation_complete = True
                    self.is_animating = False
                    self.is_firing_deathblossom = False

                # Control "deathblossom" animation
                if self.is_firing_deathblossom:
                    self.deathblossom_radius += self.ANIMATION_DEATHBLOSSOM_DELTARAD_PER_FRAME

                    # Test if it is time to end the deathblossom effect
                    if self.deathblossom_radius >= self.WEAPON_DEATHBLOSSOM_MAXRADIUS:
                        self.is_firing_deathblossom = False
                        self.animation_complete = True
                        self.is_animating = False

            # Set next animation frame timestamp
            self.animate_timestamp = time_now + self.animate_frame_display_time_secs

        # Add in "deathblossom" effect to animation
        if self.is_firing_deathblossom:
            # Create new sprite to hold composite image
            w = max(self.sprite_width, 2 * self.deathblossom_radius)
            h = max(self.sprite_height, 2 * self.deathblossom_radius)
            sprite_to_display = pg.Surface((w, h))
            sprite_to_display.set_colorkey(colormap["black"])

            # Determine blit coordinates by placing sprite rectangle center on sprite_to_show rectangle center
            current_sprite_rect = self.sprite.get_rect()
            sprite_to_display_rect = sprite_to_display.get_rect()
            current_sprite_rect.centerx = sprite_to_display_rect.centerx
            current_sprite_rect.centery = sprite_to_display_rect.centery
            blit_dest = (current_sprite_rect.left, current_sprite_rect.top)

            # Draw circle and blit image over it
            pg.draw.circle(sprite_to_display, colormap["red"], (sprite_to_display_rect.centerx, sprite_to_display_rect.centery), self.deathblossom_radius, 0)
            sprite_to_display.blit(self.sprite, blit_dest)

        return sprite_to_display


    def render(self):
        if self.is_animating:
            sprite = self._animate()
        elif self.animation_complete and not self.is_alive:
            # If animation complete after dying, display nothing
            return None
        else:
            # If not animating, select sprite to display
            if self.is_thrusting:
                self.switch_sprite(1, True)
                self.is_thrusting = False
            else:
                self.switch_sprite(0, True)

            sprite = self.sprite

        # Show hitbox for debugging
        if "DEBUG_SHOW_HITBOX" in globals() and DEBUG_SHOW_HITBOX:
            _, _, w, h = sprite.get_rect()
            pg.draw.rect(sprite, colormap["red"], (int(self.shrinkhitbox_xy/2), int(self.shrinkhitbox_xy/2), w-self.shrinkhitbox_xy, h-self.shrinkhitbox_xy), 1)

        return sprite
