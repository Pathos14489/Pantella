print("Loading falloutnv_character.py")
from src.logging import logging
from src.character_managers.base_character import base_Character
logging.info("Imported required libraries in falloutnv_character.py")

manager_slug = "falloutnv"
valid_games = ["falloutnv"]

class Character(base_Character):
    def __init__(self, characters_manager, info):
        super().__init__(characters_manager, info)
        if "voice_type" in self.info:
            self.in_game_voice_model = self.info["voice_type"]
    
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