from src.logging import logging
import src.utils as utils
import json
import os
import pandas as pd
from src.character_dbs.base_character_db import CharacterDB as BaseCharacterDB
logging.info("Imported required libraries in base_character_db.py")

db_slug = "fnv_db"

class CharacterDB(BaseCharacterDB):
    def __init__(self, conversation_manager): # character_database_directory is the path to a character directory where each character is a separate json file
        super().__init__(conversation_manager)

    def format_character(self, character):
        # Check if character card v2
        formatted_character = {}
        if "data" in character: # Character Card V2 probably
            pantella_format = {
                "bio_url": "",
                "bio": character["data"]["description"]+"\n"+character["data"]["personality"],
                "name": character["data"]["name"],
                "voice_model": character["data"]["name"].replace(" ", ""),
                "voice_folder": character["data"]["name"].replace(" ", ""),
                "race": "Imperial",
                "gender":"",
                "species":"Human",
                "age":"Adult",
                "ref_id": "",
                "base_id": "",
                "prompt_style_override": "",
                "tts_language_override": "",
                "behavior_blacklist": [],
                "behavior_whitelist": [],
                "author and notes": "Character Card V2"
            }
            formatted_character = pantella_format
        else: # TODO: Add a proper check for Pantella Format, and setup a BaseModel for character objects
            formatted_character = {
                "bio_url": character["url"] if "url" in character else "",
                "bio": "\n".join(character["descriptions"]) if "descriptions" in character else character["bio"] if "bio" in character else character["description"] if "description" in character else "",
                "name": character["name"] if "name" in character and character["name"] != "" and str(character["name"]).lower() != "nan" else "",
                "voice_model": character["voice_type"] if "voice_type" in character else "",
                "voice_folder": character["voice_type"] if "voice_type" in character else "",
                "race": character["geck_race"] if "geck_race" in character else character["race"] if "race" in character else "",
                "gender": character["gender"] if "gender" in character else character["gender"] if "gender" in character else "",
                "species": character["race"] if "race" in character else "",
                "age": character["age"] if "age" in character else "",
                "ref_id": character["ref_id"] if "ref_id" in character and character["ref_id"] != "" and str(character["ref_id"]).lower() != "nan" else "",
                "base_id": character["base_id"] if "base_id" in character and character["base_id"] != "" and str(character["base_id"]).lower() != "nan" else "",
                "prompt_style_override": character["prompt_style_override"] if "prompt_style_override" in character else "",
                "tts_language_override": character["tts_language_override"] if "tts_language_override" in character else "",
                "behavior_blacklist": character["behavior_blacklist"] if "behavior_blacklist" in character else [],
                "behavior_whitelist": character["behavior_whitelist"] if "behavior_whitelist" in character else [],
                "notes": character["author and notes"] if "author and notes" in character else character["notes"] if "notes" in character else ""
            }
        for key in formatted_character:
            if str(formatted_character[key]).lower() == "nan":
                formatted_character[key] = ""
        if "ref_id" in formatted_character and formatted_character["ref_id"] != None and len(formatted_character["ref_id"]) > 6:
            formatted_character["ref_id"] = formatted_character["ref_id"][-6:]
        if "base_id" in formatted_character and formatted_character["base_id"] != None and len(formatted_character["base_id"]) > 6:
            formatted_character["base_id"] = formatted_character["base_id"][-6:]
        # print(json.dumps(character, indent=4))
        # print(json.dumps(formatted_character, indent=4))
        # input("Press Enter to continue...")
        return formatted_character