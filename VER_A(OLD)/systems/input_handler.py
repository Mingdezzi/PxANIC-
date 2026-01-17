import pygame

class InputHandler:
    def __init__(self):
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        self.keys = {}

    def update(self):
        self.keys = pygame.key.get_pressed()
        self.mouse_pos = pygame.mouse.get_pos()
        self.mouse_buttons = pygame.mouse.get_pressed()

    def is_key_pressed(self, key_constant):
        return self.keys[key_constant]

    def is_mouse_pressed(self, button_index):
        # 0: Left, 1: Middle, 2: Right
        return self.mouse_buttons[button_index]

    def get_mouse_pos(self):
        return self.mouse_pos
