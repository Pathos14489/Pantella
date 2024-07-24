print("Loading character_db.py...")
from src.logging import logging
import src.utils as utils
import json
import os
import pandas as pd
logging.info("Imported required libraries in character_db.py")

class CharacterDB():
    def __init__(self, conversation_manager): # character_database_directory is the path to a character directory where each character is a separate json file
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.synthesizer = conversation_manager.synthesizer
        self.character_database_path = self.config.character_database_file
        self._characters = []
        self.named_index = {}
        self.base_id_index = {}
        self.ref_id_index = {}
        self.unique_ref_index = {}
        self.valid = []
        self.invalid = []
        self.db_type = None
        # make sure voice_model_ref_ids_file exists
        if not os.path.exists(self.config.voice_model_ref_ids_file):
            logging.error(f"Could not find voice_model_ref_ids_file at {self.config.voice_model_ref_ids_file}. Please download the correct file for your game, or correct the filepath in your config.json and try again.")
            raise FileNotFoundError
        if self.config.voice_model_ref_ids_file != "" and os.path.exists(self.config.voice_model_ref_ids_file):
            with open(self.config.voice_model_ref_ids_file, 'r') as f:
                self.voice_model_ids = json.load(f)
        else:
            self.voice_model_ids = {}
            
        logging.info(f"Loading default character database from {self.character_database_path}...")
        self.load(self.character_database_path)
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if addon['enabled'] and "characters" in addon['addon_parts']:
                addon_characters_directory = os.path.abspath(os.path.join(self.config.addons_dir, addon_slug, "characters"))
                logging.info(f"Loading addon character database from {addon_characters_directory}...")
                self.load(addon_characters_directory)

    def loaded(self):
        logging.info(f"{len(self.male_voice_models)} Male voices - {len(self.female_voice_models)} Female voices")
        logging.config("All Required Voice Models: "+str(self.all_voice_models))
        logging.config("Total Required Voice Models: "+str(len(self.all_voice_models)))
        logging.config("voice_model_ids:",self.voice_model_ids)

    def load(self, character_database_path):
        try:
            paths = []
            if type(character_database_path) == list:
                logging.info(f"Loading multiple character databases from {character_database_path}...")
                paths = self.character_database_path
            else:
                logging.info(f"Loading character database from {character_database_path}...")
                paths = [character_database_path]
            for path in paths:
                if character_database_path.endswith('.csv'):
                    logging.info("Loading character database from csv...")
                    self.load_characters_csv(path)
                else:
                    logging.info("Loading character database from json...")
                    self.load_characters_json(path)
                self.verify_characters()
                self.loaded()
        except Exception as e:
            logging.error(f"Could not load character database from {character_database_path}. Please check the path and try again. Path should be a directory containing json files or a csv file containing character information.")
            logging.error(e)
            raise

    def load_characters_json(self, path=None):
        count_before = len(self._characters)
        if path is None:
            path = self.character_database_path
        if type(path) == list:
            path = path[0]
        logging.info(f"Loading character database from JSON files {path}...")
        for file in os.listdir(path):
            if file.endswith(".json"):
                character = json.load(open(os.path.join(path, file)))
                character = self.format_character(character)
                self._characters.append(character)
                self.unique_ref_index[f"{character['name']}({character['ref_id']})[{character['base_id']}]"] = character
                if character['name'] != None and character['name'] != "" and character['name'] != "nan":
                    self.named_index[character['name']] = character
                if character['base_id'] != None and str(character['base_id']) != "" and str(character['base_id']) != "nan":
                    self.base_id_index[character['base_id']] = character
                if character['ref_id'] != None and str(character['ref_id']) != "" and str(character['ref_id']) != "nan":
                    self.ref_id_index[character['ref_id']] = character
        if self.db_type != None and self.db_type != 'json':
            self.db_type = 'mixed'
        else:
            self.db_type = 'json'
        logging.info(f"Loaded {len(self._characters)-count_before} characters from json files {path}")
    
    def load_characters_csv(self, path=None):
        if path is None:
            path = self.character_database_path
        if type(path) == list:
            path = path[0]
        logging.info(f"Loading character database from CSV at '{path}'...")
        encoding = utils.get_file_encoding(path)
        character_database = pd.read_csv(path, engine='python', encoding=encoding)
        character_database = character_database.loc[character_database['voice_model'].notna()]
        for _, row in character_database.iterrows():
            character = row.to_dict()
            character = self.format_character(character)
            self._characters.append(character)
            self.unique_ref_index[f"{character['name']}({character['ref_id']})[{character['base_id']}]"] = character
            if character['name'] != None and character['name'] != "" and character['name'] != "nan":
                self.named_index[character['name']] = character
            if character['base_id'] != None and str(character['base_id']).strip() != "" and str(character['base_id']).strip().lower() != "nan":
                self.base_id_index[character['base_id']] = character
            if character['ref_id'] != None and str(character['ref_id']).strip() != "" and str(character['ref_id']).strip().lower() != "nan":
                self.ref_id_index[character['ref_id']] = character
        if self.db_type != None and self.db_type != 'csv':
            self.db_type = 'mixed'
        else:
            self.db_type = 'csv'
        logging.info(f"Loaded {len(self.characters)} characters from csv {path}")

    def format_character(self, character):
        # Check if character card v2
        formatted_character = {}
        if "data" in character: # Character Card V2 probably
            pantella_format = {
                "bio_url": "",
                "bio": character["data"]["description"]+"\n"+character["data"]["personality"],
                "name": character["data"]["name"],
                "voice_model": character["data"]["name"].replace(" ", ""),
                "skyrim_voice_folder": character["data"]["name"].replace(" ", ""),
                "race": "Imperial",
                "gender":"",
                "species":"Human",
                "age":"Adult",
                "ref_id": "",
                "base_id": "",
                "prompt_style_override": "",
                "tts_language_override": "",
                "is_generic_npc": False,
                "behavior_blacklist": [],
                "behavior_whitelist": [],
                "author and notes": "Character Card V2"
            }
            formatted_character = pantella_format
        else: # TODO: Add a proper check for Pantella Format, and setup a BaseModel for character objects
            formatted_character = {
                "bio_url": character["bio_url"] if "bio_url" in character else "",
                "bio": character["bio"] if "bio" in character and character["bio"] != "" and str(character["bio"]).lower() != "nan" else "",
                "name": character["name"] if "name" in character and character["name"] != "" and str(character["name"]).lower() != "nan" else "",
                "voice_model": character["voice_model"] if "voice_model" in character else "",
                "skyrim_voice_folder": character["skyrim_voice_folder"] if "skyrim_voice_folder" in character else "",
                "race": character["in_game_race"] if "in_game_race" in character else character["race"] if "race" in character else "",
                "gender": character["in_game_gender"] if "in_game_gender" in character else character["gender"] if "gender" in character else "",
                "species": character["species"] if "species" in character else "",
                "age": character["age"] if "age" in character else "",
                "ref_id": character["ref_id"] if "ref_id" in character and character["ref_id"] != "" and str(character["ref_id"]).lower() != "nan" else "",
                "base_id": character["base_id"] if "base_id" in character and character["base_id"] != "" and str(character["base_id"]).lower() != "nan" else "",
                "prompt_style_override": character["prompt_style_override"] if "prompt_style_override" in character else "",
                "tts_language_override": character["tts_language_override"] if "tts_language_override" in character else "",
                "is_generic_npc": character["is_generic_npc"] if "is_generic_npc" in character else False,
                "behavior_blacklist": character["behavior_blacklist"] if "behavior_blacklist" in character else [],
                "behavior_whitelist": character["behavior_whitelist"] if "behavior_whitelist" in character else [],
                "notes": character["author and notes"] if "author and notes" in character else character["notes"] if "notes" in character else ""
            }
        for key in formatted_character:
            if str(formatted_character[key]).lower() == "nan":
                formatted_character[key] = ""
        return formatted_character

    def get_unique_ref_index(self,character):
        return self.unique_ref_index[f"{character['name']}({character['ref_id']})[{character['base_id']}]"]

    @property
    def characters(self):
        filtered = []
        for character in self._characters:
            if character['name'] != None and character['name'] != "" and str(character['name']).lower() != "nan":
                filtered.append(character)
        sorted_characters = sorted(filtered, key=lambda x: str(x['name']))
        return sorted_characters

    def patch_character_info(self,info): # Patches information about a character into the character database and if db_type is json, saves the changes to the json file
        info = self.format_character(info)
        if info['name'] != None and info['name'] != "" and info['name'] != "nan":
            self._characters.append(info)
            self.named_index[info['name']] = self.characters[-1]
            self.base_id_index[info['base_id']] = self.characters[-1] 
            self.ref_id_index[info['ref_id']] = self.characters[-1]
            if self.db_type == 'json':
                if not os.path.exists(self.character_database_path): # If the directory doesn't exist, create it
                    os.makedirs(self.character_database_path) 
                json_file_path = os.path.join(self.character_database_path, info['name']+'.json')
                # If the character already exists, confirm that the user wants to overwrite it
                if os.path.exists(json_file_path):
                    overwrite = input(f"Character '{info['name']}' already exists in the database. Overwrite? (y/n): ")
                    if overwrite.lower() != 'y':
                        return
                json.dump(info, open(json_file_path, 'w'), indent=4)

    def get_character_by_name(self, name):
        if name in self.named_index:
            return self.named_index[name]
        else:
            logging.warning(f"Could not find character '{name}' in character database using name lookup.")
            return None
        
    def get_character_by_voice_folder(self, voice_folder): # Look through non-generic characters for a character with the given voice folder
        for character in self.characters:
            if character['voice_model'].lower() == voice_folder.lower(): # If the voice model matches, return the character
                return character
        return None # If no character is found, return None
    
    def get_voice_folder_by_voice_model(self, voice_model):
        # logging.info(f"voice_model_ids: {voice_model}/{voice_model.replace(' ', '')}")
        folder = None
        for voice_folder in self.voice_folders:
            if voice_model == voice_folder:
                folder = self.voice_folders[voice_folder]
            if voice_model.replace(' ', '') == voice_folder:
                folder = self.voice_folders[voice_folder]
        # logging.info(f"folder:",folder)
        if folder == None:
            folder = voice_model.replace(' ', '')
            logging.warning(f"Could not find voice folder for voice model '{voice_model}', defaulting to '{folder}'")
        if type(folder) == list:
            folder = folder[0]
        return folder
    
    def verify_characters(self):
        synthesizer_available_voices = self.synthesizer.voices()
        self.valid = []
        self.invalid = []
        self.unused_voices = []
        for voice in self.all_voice_models:
            # spaced_voice = ""
            # for letter in voice.replace(' ', ''):
            #     if letter.isupper():
            #         spaced_voice += " "
            #     spaced_voice += letter
            # unspaced_voice = voice.replace(' ', '')
            # lowercase_voice = voice.lower()
            # unspaced_lowercase_voice = unspaced_voice.lower()
            # voice_folder = self.get_voice_folder_by_voice_model(voice)
            # if voice_folder == None:
            #     voice_folder = voice
            # lower_voice_folder = voice_folder.lower()
            # if voice_folder in synthesizer_available_voices:
            #     self.valid.append(voice_folder)
            # elif lower_voice_folder in synthesizer_available_voices:
            #     self.valid.append(lower_voice_folder)
            # elif voice in synthesizer_available_voices:
            #     self.valid.append(voice)
            # elif unspaced_voice in synthesizer_available_voices:
            #     self.valid.append(unspaced_voice)
            # elif spaced_voice in synthesizer_available_voices:
            #     self.valid.append(spaced_voice)
            # elif lowercase_voice in synthesizer_available_voices:
            #     self.valid.append(lowercase_voice)
            # elif unspaced_lowercase_voice in synthesizer_available_voices:
            #     self.valid.append(unspaced_lowercase_voice)
            # # elif voice in self.voice_folders: # If the voice model is a valid voice folder, add it to the valid list
            # #     self.valid.append(voice.replace(' ', ''))
            voice_model = self.synthesizer.get_valid_voice_model(voice, crashable=False, log=False)
            if voice_model != None:
                self.valid.append((voice, voice_model))
            else:
                logging.warning(f"invalid voice: {voice}")
                self.invalid.append(voice)
        for voice_model_folder in self.all_voice_folders:
            voice_model = self.synthesizer.get_valid_voice_model(voice_model_folder, crashable=False, log=False)
            if voice_model not in self.valid:
                self.valid.append((voice_model_folder, voice_model))
        for voice in synthesizer_available_voices:
            # add spaces before each capital letter
            voice_used = False
            # if voice not in self.valid:
            #     self.unused_voices.append(voice)
            #     logging.config(f"unused voice: {voice}")
            for voice_pair in self.valid:
                voice_model, voice_2 = voice_pair
                if voice == voice_model or voice == voice_2:
                    voice_used = True
                    break
            if not voice_used:
                self.unused_voices.append(voice)
                logging.config(f"unused voice: {voice}")
        # new_valid = []
        # for voice_pair in self.valid:
        #     voice, voice_model = voice_pair
        #     if voice not in self.unused_voices and voice_model not in self.unused_voices:
        #         new_valid.append(voice)
        # self.valid = new_valid
        for voice in self.unused_voices:
            for character in self.characters:
                if character['skyrim_voice_folder'] == voice or character['voice_model'] == voice:
                    logging.info(f"Character '{character['name']}' uses unused voice model '{voice}'")
        logging.config(f"Valid voices found in character database: {len(self.valid)}/{len(self.all_voice_models)}")

        logging.config(f"Total unused voices: {len(self.unused_voices)}/{len(synthesizer_available_voices)}")
        if len(self.invalid) > 0:
            logging.warning(f"Invalid voices found in character database: {self.invalid}. Please check that the voices are installed and try again.")
            for character in self.characters:
                if character['voice_model'] in self.invalid:
                    if character['voice_model'] != "":
                        logging.warning(f"Character '{character['name']}' uses invalid voice model '{character['voice_model']}'! This is an error, please report it! (The rest of the program will continue to run, but this character might not be able to be used)")

    def get_character(self, character_name, character_ref_id=None, character_base_id=None): # Get a character from the character database using the character's name, refid_int, or baseid_int
        if character_ref_id is not None:
            if str(character_ref_id).lower() == "nan":
                character_ref_id = None
            if type(character_ref_id) == float:
                character_ref_id = int(character_ref_id)
        if character_base_id is not None:
            if str(character_base_id).lower() == "nan":
                character_base_id = None    
            if type(character_base_id) == float:
                character_base_id = int(character_base_id)
        if character_ref_id.strip() == "":
            character_ref_id = None
        if character_base_id.strip() == "":
            character_base_id = None
        logging.info(f"Getting character '{character_name}({character_ref_id})[{character_base_id}]'...")
        try:
            character_ref_id = int(character_ref_id) if character_ref_id is not None else 0 # Convert int id to hex if it is not None
            logging.info("character_ref_id is int:",character_ref_id)
        except: # Hex
            try:
                character_ref_id = int(character_ref_id, 16) if character_ref_id is not None else 0
                logging.info("character_ref_id is hex:",character_ref_id)
            except:
                logging.error(f"Could not convert ref_id '{character_ref_id}' to int or hex.")
        try:
            character_base_id = int(character_base_id) if character_base_id is not None else 0 # Convert int id to hex if it is not None
            logging.info("character_base_id is int:",character_base_id)
        except: # Hex
            try:
                character_base_id = int(character_base_id, 16) if character_base_id is not None else 0
                logging.info("character_base_id is hex:",character_base_id)
            except:
                logging.error(f"Could not convert base_id '{character_base_id}' to int or hex.")
        if type(character_ref_id) == str:
            try:
                character_ref_id = int(character_ref_id, 16)
            except:
                try:
                    character_ref_id = int(character_ref_id)
                except:
                    logging.error(f"Could not convert ref_id string '{character_ref_id}' to hex or int.")
        if type(character_base_id) == str:
            try:
                character_base_id = int(character_base_id, 16)
            except:
                try:
                    character_base_id = int(character_base_id)
                except:
                    logging.error(f"Could not convert base_id string '{character_base_id}' to hex or int.")
        character_ref_id = abs(character_ref_id)
        logging.info(f"character_ref_id abs: {character_ref_id}")
        character_base_id = abs(character_base_id)
        logging.info(f"character_base_id abs: {character_base_id}")
        logging.info(f"Getting character '{character_name}({character_ref_id})[{character_base_id}]<({hex(character_ref_id)})[{hex(character_base_id)}]>'...")
        # TODO: is the 3: correct or should it be 2:?
        character_ref_id = hex(character_ref_id)[3:] if character_ref_id is not None else 0 # Convert int id to hex if it is not None
        character_base_id = hex(character_base_id)[3:] if character_base_id is not None else 0 # Convert int id to hex if it is not None
        logging.info(f"Fixed IDs: '{character_name}({character_ref_id})[{character_base_id}]' - Getting character from character database using name lookup...")
        return self._get_character(character_name, character_ref_id, character_base_id)

    def _get_character(self, character_name, character_ref_id=None, character_base_id=None): # Get a character from the character database using the character's name, refid_int, or baseid_int
        logging.info(f"_getting character '{character_name}({character_ref_id})[{character_base_id}]'...")
        possibly_same_character = []
        character = None
        is_generic_npc = False
        if str(character_name) == "nan":
            character_name = None
            logging.info(f"character_name is None: {character_name}")
        if character_ref_id is not None and str(character_ref_id).strip() == "" or character_ref_id == 0:
            character_ref_id = None
            logging.info(f"character_ref_id is None: {character_ref_id}")
        if character_base_id is not None and str(character_base_id).strip() == "" or character_base_id == 0:
            character_base_id = None
            logging.info(f"character_base_id is None: {character_base_id}")

        # if at least something can't be used to find the character with, return None,None
        if character_name is None and character_ref_id is None and character_base_id is None:
            logging.error(f"Could not find character '{character_name}' in character database.")
            # TODO: Character generation
            return None, None, {"name": False, "ref_id": False, "base_id": False}
        
        # logging.info(f"Getting character '{character_name}({character_ref_id})[{character_base_id}]' associations from character database...")
        # for db_character in self.characters: # Try to find any character with the same name and ref_id and add it to the possibly_same_character list
        #     if character_name is not None and character_name.lower() == str(db_character['name']).lower():
        #         possibly_same_character.append(db_character)
        #         logging.info(f"Found possible character '{db_character['name']}' association in character database using name lookup.")
        #     elif character_ref_id is not None and (character_ref_id == db_character['ref_id'] or str(character_ref_id).endswith(str(db_character["ref_id"]))):
        #         possibly_same_character.append(db_character)
        #         logging.info(f"Found possible character '{db_character['name']}' association in character database using ref_id lookup.")
        #     elif character_base_id is not None and (character_base_id == db_character['base_id'] or str(character_base_id).endswith(str(db_character["base_id"]))):
        #         possibly_same_character.append(db_character)
        #         logging.info(f"Found possible character '{db_character['name']}' association in character database using base_id lookup.")
        character_match = None
        is_generic_npc = False
        matching_parts = {
            "name": False,
            "ref_id": False,
            "base_id": False
        }
        character_ref_id = str(character_ref_id)
        character_base_id = str(character_base_id)
        # Unique Reference Lookup
        logging.info(f"Performing unique reference lookup for character '{str(character_name)}({str(character_ref_id)})[{str(character_base_id)}]'")
        if character_name is not None and character_ref_id is not None and character_base_id is not None:
            if f"{character_name}({character_ref_id})[{character_base_id}]" in self.unique_ref_index:
                character_match = self.unique_ref_index[f"{character_name}({character_ref_id})[{character_base_id}]"]
                matching_parts = {"name": True, "ref_id": True, "base_id": True}
                logging.info(f"Found possible character '{character_name}' association in character database using unique reference lookup.")
        # Name Lookup
        logging.info(f"Performing name lookup for character '{character_name}'")
        if character_name is not None and character_match is None:
            if character_name in self.named_index:
                character_match = self.named_index[character_name]
                matching_parts = {
                    "name": True,
                    "ref_id": character_match['ref_id'] == character_ref_id,
                    "base_id": character_match['base_id'] == character_base_id
                }
                logging.info(f"Found possible character '{character_name}' association in character database using name lookup.")
        # Ref/Base ID Lookup
        logging.info(f"Performing ref_id and base_id lookup for character '{character_ref_id}({character_base_id})'")
        if character_ref_id is not None and character_base_id is not None and character_match is None:
            for db_character in self._characters:
                if ((str(db_character['ref_id']).endswith(character_ref_id) and str(db_character['base_id']).endswith(character_base_id))) or ((str(db_character['ref_id']).upper().endswith(character_ref_id.upper()) and str(db_character['base_id']).upper().endswith(character_base_id.upper()))):
                    character_match = db_character
                    matching_parts = {
                        "name": character_match['name'] == character_name,
                        "ref_id": True,
                        "base_id": True
                    }
                    logging.info(f"Found possible character '{character_name}' association in character database using ref_id and base_id lookup.")
                    break
        # Exact Base ID Lookup
        logging.info(f"Performing exact base_id lookup for character '{character_base_id}'")
        if character_base_id is not None and character_match is None:
            if character_base_id in self.base_id_index or str(character_base_id).upper() in self.base_id_index:
                character_match = self.base_id_index[character_base_id]
                matching_parts = {
                    "name": character_match['name'] == character_name,
                    "ref_id": character_match['ref_id'] == character_ref_id,
                    "base_id": True
                }
                is_generic_npc = character_match['is_generic_npc'] if "is_generic_npc" in character_match else True
                logging.info(f"Found possible character '{character_name}' association in character database using base_id lookup.")
        # Endswith Base ID Lookup
        logging.info(f"Performing endswith base_id lookup for character '{character_base_id}'")
        if character_base_id is not None and character_match is None:
            for db_character in self._characters:
                if str(db_character['base_id']).endswith(character_base_id) or str(db_character['base_id']).upper().endswith(character_base_id.upper()):
                    character_match = db_character
                    matching_parts = {
                        "name": character_match['name'] == character_name,
                        "ref_id": character_match['ref_id'] == character_ref_id,
                        "base_id": True
                    }
                    is_generic_npc = character_match['is_generic_npc'] if "is_generic_npc" in character_match else True
                    logging.info(f"Found possible character '{character_name}' association in character database using base_id lookup.")
                    break
        logging.info(f"Character Match:",character_match)
        logging.info(f"Matching Parts:",matching_parts)
        return character_match, is_generic_npc, matching_parts

    def has_character(self, character):
        if str(character['name']) == "nan":
            print("character:",character)
        character, is_generic_npc, matching_parts = self.get_character(character['name'], character['ref_id'], character['base_id'])
        if character is not None:
            return character, is_generic_npc, matching_parts
        return None, False, matching_parts
    
    def compare(self,db): # Compare this DB with another DB and return the differences - Useful for comparing a DB with a DB that has been patched, can be used to generate changelogs
        differences = []
        for character in self.characters: # Compare each character in the DB with the other DB
            if character['name'] == "nan" or character['name'].strip() == "" or character['name'] == None:
                logging.info(f"Skipping character with no name: {character}")
                continue
            diff = False
            db_character, is_generic_npc, matching_parts = db.has_character(character)
            match_type = None
            character["is_generic_npc"] = is_generic_npc
            character["matching_parts"] = matching_parts
            if matching_parts["name"] and matching_parts["ref_id"] and matching_parts["base_id"]:
                match_type = "exact_match"
            elif matching_parts["name"] and matching_parts["ref_id"] and not matching_parts["base_id"]:
                match_type = "name_ref_id_match"
            elif matching_parts["name"] and matching_parts["base_id"] and not matching_parts["ref_id"]:
                match_type = "name_base_id_match"
            elif matching_parts["name"] and not matching_parts["ref_id"] and not matching_parts["base_id"]:
                match_type = "name_match"
            elif matching_parts["ref_id"] and not matching_parts["name"] and not matching_parts["base_id"]:
                match_type = "ref_id_only_match"
            elif matching_parts["base_id"] and not matching_parts["name"] and not matching_parts["ref_id"]:
                match_type = "base_id_only_match"
            character['match_type'] = match_type
            logging.info(f"Match Type: {match_type}")
            if db_character == None: # If the character is not in the other DB, add it to the differences list
                character['differences'] = ["removed_character"]
            elif match_type != None: # If the character is in the other DB, check for differences -- Can false report variants of the same character name as different characters
                logging.info(f"Comparing character '{character['name']}' to character '{db_character['name']}' in the other DB...")
                character['differences'] = []
                for key in character:
                    if key in db.named_index[character['name']]:
                        if str(character[key]) != str(db.named_index[character['name']][key]):
                            character['differences'].append({"key":key,"other":db.named_index[character['name']][key]})
                            diff = True
            if diff:
                differences.append(character)
        for character in db.characters: # Compare each character in the other DB with this DB
            if character['name'] == "nan" or character['name'] == "" or character['name'] == None:
                continue
            diff = False
            self_character, is_generic_npc, matching_parts = self.has_character(character)
            match_type = None
            character["is_generic_npc"] = is_generic_npc
            character["matching_parts"] = matching_parts
            if matching_parts["name"] and matching_parts["ref_id"] and matching_parts["base_id"]:
                match_type = "exact_match"
            elif matching_parts["name"] and matching_parts["ref_id"] and not matching_parts["base_id"]:
                match_type = "name_ref_id_match"
            elif matching_parts["name"] and matching_parts["base_id"] and not matching_parts["ref_id"]:
                match_type = "name_base_id_match"
            elif matching_parts["name"] and not matching_parts["ref_id"] and not matching_parts["base_id"]:
                match_type = "name_match"
            elif matching_parts["ref_id"] and not matching_parts["name"] and not matching_parts["base_id"]:
                match_type = "ref_id_only_match"
            elif matching_parts["base_id"] and not matching_parts["name"] and not matching_parts["ref_id"]:
                match_type = "base_id_only_match"
            character['match_type'] = match_type
            if self_character == None: # If the character is not in this DB, add it to the differences list
                character['differences'] = ["added_character"]
            elif match_type != None: # If the character is in this DB, check for differences
                character['differences'] = []
                for key in character:
                    if key in self.named_index[character['name']]:
                        if str(character[key]) != str(self.named_index[character['name']][key]):
                            character['differences'].append({"key":key,"other":self.named_index[character['name']][key]})
                            diff = True
            if diff:
                differences.append(character)
        for folder in self.voice_folders:
            if folder not in db.voice_folders:
                differences.append({"voice_model":folder,"difference_reason":"Voice model not found in other DB","diff_type":"removed_voice_folder"})
        for folder in db.voice_folders:
            if folder not in self.voice_folders:
                differences.append({"voice_model":folder,"difference_reason":"Voice model added found in other DB","diff_type":"added_voice_folder"})
        for voice_model in self.all_voice_models:
            if voice_model not in db.all_voice_models:
                differences.append({"voice_model":voice_model,"difference_reason":"Voice model not found in other DB","diff_type":"removed_voice_model"})
        for voice_model in db.all_voice_models:
            if voice_model not in self.all_voice_models:
                differences.append({"voice_model":voice_model,"difference_reason":"Voice model not found in this DB","diff_type":"added_voice_model"})
        for unused_voice in db.unused_voices:
            if unused_voice not in self.unused_voices:
                related_characters = []
                for character in db.characters:
                    if character['skyrim_voice_folder'] == unused_voice or character['voice_model'] == unused_voice:
                        related_characters.append(character['name'])
                differences.append({"voice_model":unused_voice,"difference_reason":"Unused voice model found in other DB","diff_type":"added_unused_voice"})
        for unused_voice in self.unused_voices:
            if unused_voice not in db.unused_voices:
                related_characters = []
                for character in self.characters:
                    if character['skyrim_voice_folder'] == unused_voice or character['voice_model'] == unused_voice:
                        related_characters.append(character['name'])
        if len(self.characters) > len(db.characters):
            differences.append({"difference_reason":"This DB has more characters than the other DB (This is not necessarily an error, if there are not missing characters, this might mean that the original DB had duplicates that were automatically removed!)", "characters":len(self.characters), "db_characters":len(db.characters), "diff_type":"edited_character_count"})
        elif len(self.characters) < len(db.characters):
            differences.append({"difference_reason":"This DB has less characters than the other DB -- The other DB might have added new characters!", "characters":len(self.characters), "db_characters":len(db.characters), "diff_type":"edited_character_count"})
        return differences
    
    def save(self, path, type='json'): # Save the character database to a json directory or csv file
        # self.characters.sort(key=lambda x: str(x['name']))
        if type == 'json':
            if not os.path.exists(path):
                os.makedirs(path)
            for character in self._characters:
                json_file_path = os.path.join(path, str(self.config.game_id) + "_" + str(character['gender']) + "_" + str( character["in_game_race"] if "in_game_race" in character else character["race"] if "race" in character else "") + "_" + str(character['name']) + "_" + str(character['ref_id']) + "_" + str(character['base_id']) + '.json')
                json.dump(character, open(json_file_path, 'w'), indent=4)
        elif type == 'csv':
            df = pd.DataFrame(self._characters)
            df.to_csv(path, index=False)
        else:
            logging.error(f"Could not save character database. Invalid type '{type}'.")
            raise ValueError
        
        
    @property
    def male_voice_models(self):
        valid = {}
        for character in self._characters:
            if character["gender"].capitalize() == "Male" and "Female" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self._characters:
            race_string = str(character['race'])+"Race"
            if character["voice_model"] in filtered and character["voice_model"] != "":
                if race_string not in models:
                    models[race_string] = [character['voice_model']]
                else:
                    if character["voice_model"] not in models[race_string]:
                        models[race_string].append(character['voice_model'])
        return models
    
    @property
    def female_voice_models(self):
        valid = {}
        for character in self._characters:
            if character["gender"].capitalize() == "Female" and "Male" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self._characters:
            race_string = str(character['race'])+"Race"
            if character["voice_model"] in filtered and character["voice_model"] != "":
                if race_string not in models:
                    models[race_string] = [character['voice_model']]
                else:
                    if character["voice_model"] not in models[race_string]:
                        models[race_string].append(character['voice_model'])
        return models
    
    @property
    def all_voice_models(self):
        models = []
        for character in self.characters:
            if character["voice_model"] != "":
                if character["voice_model"] not in models:
                    models.append(character["voice_model"])
        models = [model for model in models if model != "" and model != "nan" and model != None]
        models = list(set(models))
        models = sorted(models)
        return models
        
    @property
    def voice_folders(self): # Returns a dictionary of voice models and their corresponding voice folders
        folders = {} 
        for character in self.characters:
            if character['voice_model'] != "":
                if character['voice_model'] not in folders:
                    if character['skyrim_voice_folder'] != "":
                        folders[character['voice_model']] = [character['skyrim_voice_folder']]
                    else:
                        folders[character['voice_model']] = [character['voice_model']]
                else:
                    if character["skyrim_voice_folder"] not in folders[character['voice_model']]:
                        if character['skyrim_voice_folder'] != "":
                            folders[character['voice_model']].append(character['skyrim_voice_folder'])
                        else:
                            folders[character['voice_model']].append(character['voice_model'])
        return folders
    
    @property
    def all_voice_folders(self):
        folders = []
        for character in self.characters:
            if character['skyrim_voice_folder'] != "":
                if character['skyrim_voice_folder'] not in folders:
                    folders.append(character['skyrim_voice_folder'])
        folders = [folder for folder in folders if folder != "" and folder != "nan" and folder != None]
        folders = list(set(folders))
        folders = sorted(folders)
        return folders