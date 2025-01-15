print("Loading character_manager.py")
from src.logging import logging
import os
import src.memory_manager as mm
import json
import random
from src.character_managers.base_character import base_Character
logging.info("Imported required libraries in character_manager.py")

manager_slug = "skyrim"
valid_games = ["skyrim","skyrimvr"]

class Character(base_Character):
    def __init__(self, characters_manager, info):
        super().__init__(characters_manager, info)
    
    @property
    def race(self):
        race = "Imperial"
        if "race" in self.info and self.info["race"] != None and self.info["race"] != "":
            race = self.info["race"]
        elif "in_game_race" in self.info and self.info["in_game_race"] != None and self.info["in_game_race"] != "":
            race = self.info["in_game_race"]
        # if race.lower().capitalize() in self.language["race_titles"]: # Infinte recursion error with language property
        #     race = self.language["race_titles"][race.lower().capitalize()]
        return race
    
    @property
    def in_game_race(self):
        race = "Imperial"
        if "in_game_race" in self.info and self.info["in_game_race"] != None and self.info["in_game_race"] != "":
            race = self.info["in_game_race"]
        return race