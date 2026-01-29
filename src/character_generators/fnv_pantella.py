print("Importing simple_generator.py")
from src.logging import logging
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
logging.info("Imported required libraries in simple_generator.py")

generator_name = "fnv_pantella"
valid_games = ["falloutnv"]

class Character(BaseModel):
    """Fallout: New Vegas Character Schema - Uses Fallout: New Vegas Stats, Stats are all 0-100"""
    name: str = Field(...,min_length=1)
    personality_description: str = Field(...,min_length=1)
    backstory: str = Field(...,description="A description of the character's backstory. Should be at least a paragraph long.")
    current_scenario: str = Field(...,description="A description of what the character is currently doing. Should be at least a sentence long.")
    race: str = Field(...,examples=["Argonian","Breton","Dark Elf","High Elf","Imperial","Khajiit","Nord","Orc","Redguard","Wood Elf"],pattern="^(Argonian|Breton|Dark Elf|High Elf|Imperial|Khajiit|Nord|Orc|Redguard|Wood Elf)$")
    gender: str = Field(...,examples=["Male","Female"],pattern="^(Male|Female)$")
    species: str = Field(...,examples=["Human","Elf","Argonian","Khajiit","Daedra", "Divine", "Dragon", "Goblin", "Atronach"], pattern="^(Human|Elf|Argonian|Khajiit|Daedric|Divine|Dragon|Goblin|Atronach|Giant)$")
    lang_override: str = Field(...,description="The language/accent to use for the voice lines.",examples=["en","es","fr","de","it","ja","ko","pl","pt","ru","zh"],pattern="^(en|es|fr|de|it|ja|ko|pl|pt|ru|zh)$")
    voice_model: str = Field(...,description="The voice model to use for the character.",examples=["FemaleArgonian","MaleArgonian","FemaleDarkElf","FemaleElfHaughty","FemaleCommander", "FemaleCondescending","FemaleEvenToned","FemaleKhajiit","FemaleNord","FemaleOldGrumpy","FemaleOldKindly","FemaleOrc", "FemaleShrill", "FemaleSultry", "FemaleYoungEager","MaleArgonian", "MaleBandit", "MaleBrute", "MaleCommander","MaleCommoner","MaleCommonerAccented", "MaleCondescending","MaleCoward","MaleDarkElf","MaleDrunk","MaleElfHaughty","MaleEvenToned","MaleEvenTonedAccented", "MaleKhajiit","MaleNord","MaleOldGrumpy","MaleOldKindly","MaleOrc","MaleSlyCynical","MaleSoldier","MaleYoungEager"], pattern="^(FemaleArgonian|MaleArgonian|FemaleDarkElf|FemaleElfHaughty|FemaleCommander|FemaleCondescending|FemaleEvenToned|FemaleKhajiit|FemaleNord|FemaleOldGrumpy|FemaleOldKindly|FemaleOrc|FemaleShrill|FemaleSultry|FemaleYoungEager|MaleArgonian|MaleBandit|MaleBrute|MaleCommander|MaleCommoner|MaleCommonerAccented|MaleCondescending|MaleCoward|MaleDarkElf|MaleDrunk|MaleElfHaughty|MaleEvenToned|MaleEvenTonedAccented|MaleKhajiit|MaleNord|MaleOldGrumpy|MaleOldKindly|MaleOrc|MaleSlyCynical|MaleSoldier|MaleYoungEager)$")
    
    def get_prompt(character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, location=None):
        if location is None:
            location = "Fallout: New Vegas"
        return f"Create a Fallout: New Vegas character named {character_name} with the following information: Character is a {character_in_game_gender} {character_in_game_race}.\nThey are currently located at: {location}" # {'The character is a guard. ' if character_is_guard else ''}{'The character is a ghost. ' if character_is_ghost else ''}

    def get_chracter_info(self, ref_id, base_id, voice_model=None):
        return {
        "bio_url": "(Generated)",
        "bio": self.backstory + "\n\n" + self.current_scenario,
        "name": self.name,
        "voice_model": voice_model if voice_model is not None else self.voice_model,
        "voice_folder": voice_model if voice_model is not None else self.voice_model,
        "race": self.race,
        "gender": self.gender,
        "species": self.species,
        "ref_id": ref_id,
        "base_id": base_id,
        "lang_override": self.lang_override,
        "behavior_blacklist": [],
        "behavior_whitelist": [],
        "notes": "",
    }