#!/bin/python3
import blessed
from sys import stdout
from enum import Enum
import random
from time import sleep
from threading import Thread, Event

term = blessed.Terminal()


# style params
center = (term.width // 2, term.height // 2)
margin = 2
border_top = margin
border_bottom = term.height - margin
border_right = term.width - margin
border_left = margin

char = ' '
snake_head_horizontal_char = ':'
snake_head_vertical_char = '"'
snake_body_color = term.on_greenyellow
snake_head_color = term.black_on_red3
fruit_color = term.on_orangered
game_over_color = term.black_on_red
border_color = term.on_white
score_color = term.red
gameover_box_len = 50

# game params
grow_rate = 15
tick = 0.04
death_efffect_rate = tick / 4  # fraction of tick
death_effect_rest = 1  # time death effect stays on screen after completion
font_ratio = 2  # font height / width


class State():
    def __init__(self):
        self.snake = []
        self.facing = None
        self.moving = None
        self.fruit = None
        self.length = 0


class Compass(Enum):
    NORTH = (0, -1)
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)


# convenience functions
ld = stdout.write


def out(s):
    ld(s)
    stdout.flush()


# runs in daemon, updates state.facing with latest inpt
def handle_input(state, interrupt):
    while not interrupt.is_set():
        inp = term.inkey(timeout=1)
        moving = state.moving
        # facing cannot be changed to a direction opposite moving
        if inp.name == "KEY_UP" and moving != Compass.SOUTH.value:
            state.facing = Compass.NORTH.value
        elif inp.name == "KEY_RIGHT" and moving != Compass.WEST.value:
            state.facing = Compass.EAST.value
        elif inp.name == "KEY_DOWN" and moving != Compass.NORTH.value:
            state.facing = Compass.SOUTH.value
        elif inp.name == "KEY_LEFT" and moving != Compass.EAST.value:
            state.facing = Compass.WEST.value


# build initial snake, at grow_rate long with the head at last index
def new_snake(state):
    moving = state.moving

    # set head of snake to the center of the screen
    # create body of snake in the opposite direction of state.moving
    # (hence the '- moving' intead of '+ moving')
    # backwards list, grow_rate-1 -> 0 so that the head is the last element
    snake = [(center[0] - (moving[0] * i), center[1] - (moving[1] * i))
             for i in range(grow_rate - 1, -1, -1)]
    return snake


def new_fruit(state):
    snake = state.snake

    while True:
        fruit = (random.randint(border_left + 1, border_right - 1),
                 random.randint(border_top + 1, border_bottom - 1))
        if fruit not in snake:
            break
    return fruit


def snake_head(state):
    if state.moving in (Compass.EAST.value, Compass.WEST.value):
        return snake_head_horizontal_char
    return snake_head_vertical_char


def draw_death(state, tail):
    snake = state.snake
    head = snake[-2]
    if tail is not None:
        snake = [tail] + snake
    out(game_over_color)
    # going from head to tail.
    # -2 because we dont want to draw the overlapping segment
    for i in range(len(snake) - 2, -1, -1):
        ld(term.move_xy(snake[i][0], snake[i][1]))
        # draws snake head or body
        if snake[i] == head:
            ld(snake_head(state))
        else:
            ld(char)
        stdout.flush()
        sleep(death_efffect_rate)

    out(term.normal)
    sleep(death_effect_rest)


def draw_snake(state):
    ld(snake_body_color)
    for point in state.snake:
        ld(term.move_xy(point[0], point[1]))
        ld(char)
    ld(snake_head_color)
    ld(term.move_xy(state.snake[-1][0], state.snake[-1][1]))
    ld(snake_head(state))
    ld(term.normal)
    stdout.flush()


def draw_fruit(state):
    ld(fruit_color)
    ld(term.move_xy(state.fruit[0], state.fruit[1]))
    ld(char)
    ld(term.normal)
    stdout.flush()


def draw_border():
    ld(border_color)
    # top and bottom
    for x in range(border_left, border_right + 1):
        ld(term.move_xy(x, border_top))
        ld(char)
        ld(term.move_xy(x, border_bottom))
        ld(char)
    # left and right
    for y in range(border_top, border_bottom + 1):
        ld(term.move_xy(border_left, y))
        ld(char)
        ld(term.move_xy(border_right, y))
        ld(char)
    ld(term.normal)
    stdout.flush()


def draw_score(state):
    score = f"score: {score_color}{state.length:05}"
    len = term.length(score)
    ld(term.move_xy(border_right - len + 1, border_top - 1))
    ld(term.clear_eol)
    ld(score)
    ld(term.normal)
    stdout.flush()


def draw_state(state):
    out(term.clear)
    draw_border()
    draw_snake(state)
    draw_fruit(state)
    draw_score(state)


def wriggle_snake(state):
    # add new cell to the head of the snake
    head = (state.snake[-1][0] + state.moving[0],
            state.snake[-1][1] + state.moving[1])
    state.snake.append(head)

    # remove tail cell of snake if snake is not growing
    if state.length < len(state.snake):
        return (head, state.snake.pop(0))
    return (head,  None)


# draws state updates to the snake from wriggle_snake
def draw_wriggle(state, tail=None):
    # draw new snake head
    ld(snake_head_color)
    ld(term.move_xy(state.snake[-1][0], state.snake[-1][1]))
    ld(snake_head(state))

    # change old snake head to snake body
    ld(snake_body_color)
    ld(term.move_xy(state.snake[-2][0], state.snake[-2][1]))
    ld(char)

    # remove tail segment if present and not growing
    ld(term.normal)
    if tail is not None:
        ld(term.move_xy(tail[0], tail[1]))
        ld(char)
    stdout.flush()


def play():
    # construct initial game_state
    state = State()
    state.facing = Compass.EAST.value
    state.moving = Compass.EAST.value
    state.snake = new_snake(state)
    state.length = len(state.snake)
    state.fruit = new_fruit(state)

    inp_interrupt = Event()
    inp_thread = Thread(target=handle_input, args=[
                        state, inp_interrupt], daemon=True)
    inp_thread.start()

    # draw initial state
    draw_state(state)

    head = None
    tail = None

    while True:
        state.moving = state.facing
        head, tail = wriggle_snake(state)

        # eats a fruit
        if head == state.fruit:
            state.length += grow_rate
            state.fruit = new_fruit(state)
            draw_fruit(state)
            draw_score(state)

        # hits a wall
        x = head[0]
        y = head[1]
        if (x <= border_left or x >= border_right or
                y <= border_top or y >= border_bottom):
            break

        # hits itself
        if head in state.snake[0:-1]:
            break

        draw_wriggle(state, tail)

        # moves font_ratio times faster if moving horizontally
        if state.moving in (Compass.EAST.value, Compass.WEST.value):
            sleep(tick / font_ratio)
        else:
            sleep(tick)
    inp_interrupt.set()
    draw_death(state, tail)
    inp_thread.join()
    return game_over(state)


def game_over(state):
    out(term.clear)
    out(term.move_y(center[1]))
    out(term.move_up(2))
    out(term.center(game_over_color +
                    "GAME OVER".center(gameover_box_len) + term.normal))
    out(term.move_down)
    out(term.center(game_over_color +
        f"YOUR SCORE WAS: {state.length}".center(gameover_box_len) +
                    term.normal))
    out(term.move_down)
    out(term.center(game_over_color +
        "PRESS ENTER TO PLAY AGAIN".center(gameover_box_len) + term.normal))
    out(term.move_down)
    out(term.center(game_over_color +
        "PRESS q TO QUIT".center(gameover_box_len) + term.normal))
    while True:
        inp = term.inkey()
        if inp == "q":
            return False
        elif inp.name == "KEY_ENTER":
            return True


def main():
    play_again = True
    with term.fullscreen(), term.hidden_cursor(), term.cbreak():
        try:
            while play_again:
                play_again = play()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
