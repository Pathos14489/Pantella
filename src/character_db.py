import src.utils as utils
import src.tts as tts
import logging
import json
import os
import pandas as pd
import csv
import math
class CharacterDB():
    def __init__(self, conversation_manager): # character_database_directory is the path to a character directory where each character is a seperate json file
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.synthesizer = conversation_manager.synthesizer
        self.character_database_path = self.config.character_database_file
        self.characters = []
        self.named_index = {}
        self.base_id_index = {}
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
            
        logging.info(f"Loading character database from {self.character_database_path}...")
        try:
            if self.character_database_path.endswith('.csv'):
                logging.info("Loading character database from csv...")
                self.load_characters_csv()
            else:
                logging.info("Loading character database from json...")
                self.load_characters_json()
            self.verify_characters()
        except:
            logging.error(f"Could not load character database from {self.character_database_path}. Please check the path and try again. Path should be a directory containing json files or a csv file containing character information.")
            raise

    def loaded(self):
        logging.info(f"{len(self.male_voice_models)} Male voices - {len(self.female_voice_models)} Female voices")
        logging.info("All Required Voice Models:",self.all_voice_models)
        logging.info("Total Required Voice Models:",len(self.all_voice_models))
        logging.info("voice_model_ids:",self.voice_model_ids)

    def load_characters_json(self):
        logging.info(f"Loading character database from {self.character_database_path}...")
        self.characters = []
        self.named_index = {}
        self.base_id_index = {}
        for file in os.listdir(self.character_database_path):
            if file.endswith(".json"):
                character = json.load(open(os.path.join(self.character_database_path, file)))
                self.characters.append(character)
                self.named_index[character['name']] = self.characters[-1]
                self.base_id_index[character['base_id']] = self.characters[-1]
        self.db_type = 'json'
        logging.info(f"Loaded {len(self.characters)} characters from JSON {self.character_database_path}")
        self.loaded()
    
    def load_characters_csv(self):
        logging.info(f"Loading character database from JSON files in {self.character_database_path}...")
        self.characters = []
        self.named_index = {}
        self.base_id_index = {}
        encoding = utils.get_file_encoding(self.character_database_path)
        character_database = pd.read_csv(self.character_database_path, engine='python', encoding=encoding)
        character_database = character_database.loc[character_database['voice_model'].notna()]
        for _, row in character_database.iterrows():
            character = row.to_dict()
            self.characters.append(character)
            self.named_index[character['name']] = self.characters[-1]
            self.base_id_index[character['base_id']] = self.characters[-1]
        self.db_type = 'csv'
        logging.info(f"Loaded {len(self.characters)} characters from csv {self.character_database_path}")
        self.loaded()

    def patch_character_info(self,info): # Patches information about a character into the character database and if db_type is json, saves the changes to the json file
        self.characters.append(info)
        self.named_index[info['name']] = self.characters[-1]
        self.base_id_index[info['base_id']] = self.characters[-1] 
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
            logging.info(f"Could not find voice folder for voice model '{voice_model}', defaulting to '{folder}'")
        if type(folder) == list:
            folder = folder[0]
        return folder
    
    def verify_characters(self):
        synthesizer_available_voices = self.synthesizer.voices()
        self.valid = []
        self.invalid = []
        self.unused_voices = []
        for voice in self.all_voice_models:
            spaced_voice = ""
            for letter in voice.replace(' ', ''):
                if letter.isupper():
                    spaced_voice += " "
                spaced_voice += letter
            unspaced_voice = voice.replace(' ', '')
            voice_folder = self.get_voice_folder_by_voice_model(voice)
            if voice_folder in synthesizer_available_voices:
                self.valid.append(voice_folder)
            elif voice in synthesizer_available_voices:
                self.valid.append(voice)
            elif unspaced_voice in synthesizer_available_voices:
                self.valid.append(unspaced_voice)
            elif spaced_voice in synthesizer_available_voices:
                self.valid.append(spaced_voice)
            # elif voice in self.voice_folders: # If the voice model is a valid voice folder, add it to the valid list
            #     self.valid.append(voice.replace(' ', ''))
            else:
                logging.info(f"invalid voice: {voice_folder}")
                self.invalid.append(voice_folder)
                self.invalid.append(voice)
        for voice in synthesizer_available_voices:
            # add spaces before each capital letter
            spaced_voice = ""
            for letter in voice.replace(' ', ''):
                if letter.isupper():
                    spaced_voice += " "
                spaced_voice += letter
            unspaced_voice = voice.replace(' ', '')
            if voice not in self.valid:
                self.unused_voices.append(voice)
                logging.info(f"unused voice: {voice}")
        new_valid = []
        for voice in self.valid:
            if voice not in self.unused_voices:
                new_valid.append(voice)
        self.valid = new_valid
        for voice in self.unused_voices:
            for character in self.characters:
                if character['skyrim_voice_folder'] == voice or character['voice_model'] == voice:
                    logging.info(f"Character '{character['name']}' uses unused voice model '{voice}'")
        logging.info(f"Valid voices found in character database: {len(self.valid)}/{len(self.all_voice_models)}")

        logging.info(f"Total unused voices: {len(self.unused_voices)}/{len(synthesizer_available_voices)}")
        if len(self.invalid) > 0:
            logging.info(f"Invalid voices found in character database: {self.invalid}. Please check that the voices are installed and try again.")
            for character in self.characters:
                if character['voice_model'] in self.invalid:
                    if character['voice_model'] != "":
                        logging.info(f"WARNING: Character '{character['name']}' uses invalid voice model '{character['voice_model']}'! This is an error, please report it!")
                        logging.info("(The rest of the program will continue to run, but this character might not be able to be used)")

    def get_character(self, character_name, character_ref_id=None, character_base_id=None): # Get a character from the character database using the character's name, refid_int, or baseid_int
        character_ref_id = int(character_ref_id) if character_ref_id is not None else 0 # Convert int id to hex if it is not None
        character_base_id = int(character_base_id) if character_base_id is not None else 0 # Convert int id to hex if it is not None
        character_ref_id = abs(character_ref_id)
        character_base_id = abs(character_base_id)
        logging.info(f"Getting character '{character_name}({character_ref_id})['{character_base_id}]<({hex(character_ref_id)})['{hex(character_base_id)}]>'...")
        character_ref_id = hex(character_ref_id)[3:] if character_ref_id is not None else None # Convert int id to hex if it is not None
        character_base_id = hex(character_base_id)[3:] if character_base_id is not None else None # Convert int id to hex if it is not None
        logging.info(f"Fixed IDs: '{character_name}({character_ref_id})['{character_base_id}' - Getting character from character database using name lookup...")
        possibly_same_character = []
        character = None
        is_generic_npc = False
        for db_character in self.characters: # Try to find any character with the same name and ref_id and add it to the possibly_same_character list
            if character_name == db_character['name'] or character_ref_id == db_character['ref_id'] or db_character["ref_id"].startswith(character_ref_id):
                possibly_same_character.append(db_character)
        if len(possibly_same_character) > 0:
            if len(possibly_same_character) == 1: # If there is only one character with the same name, use that character
                if character_ref_id is not None and (character_ref_id == possibly_same_character[0]['ref_id'] or possibly_same_character[0]["ref_id"].startswith(character_ref_id)):
                    logging.info(f"Found character '{character_name}' in character database using ref_id lookup.")
                else:
                    logging.info(f"Found character '{character_name}' in character database using name lookup.")
                character = possibly_same_character[0]
            else: # If there are multiple characters with the same name, try to find one with the same ref_id
                for db_character in possibly_same_character:
                    if character_ref_id is not None and (character_ref_id == db_character['ref_id'] or db_character["ref_id"].startswith(character_ref_id)):
                        character = db_character
                        break
        if character is None: # If no character was found, try to find one with the same ref_id - This might be a generic character that doesn't have a dedicated entry in the character database
            for db_character in self.characters: # Try to find any character with the same ref_id
                if character_ref_id is not None and (character_ref_id == db_character['ref_id'] or db_character["ref_id"].startswith(character_ref_id)):
                    character = db_character
                    break
        if character is None: # If no character was found, try to find one with the same base_id - This might be a generic character that doesn't have a dedicated entry in the character database
            for db_character in self.characters: # Try to find any character with the same base_id
                if character_base_id is not None and )character_base_id == db_character['base_id'] or db_character["base_id"].startswith(character_base_id)):
                    character = db_character
                    is_generic_npc = True
                    break
        if character is None: # No character was found, print an error message and wait for the user to press enter before exiting the program
            logging.warning(f"Could not find character '{character_name}' in character database using name lookup.")
            logging.warning(f"Could not find character '{character_ref_id}' in character database using ref_id lookup.")
            logging.warning(f"Could not find character '{character_base_id}' in character database using base_id lookup.")
            logging.error(f"Could not find character '{character_name}' in character database.")
            input("Press enter to continue...")
            exit(0)
        return character, is_generic_npc

    def has_character(self, character):
        character_in_db = False
        characters_with_same_name = []
        for db_character in self.characters:
            if character['name'] == db_character['name']:
                characters_with_same_name.append(db_character)
        if len(characters_with_same_name) > 0:
            for db_character in characters_with_same_name:
                if character['ref_id'] is not None and character['ref_id'] == db_character['ref_id']:
                    character_in_db = True
                elif character['base_id'] is not None and character['base_id'] == db_character['base_id']:
                    character_in_db = True
        return character_in_db
    
    def compare(self,db): # Compare this DB with another DB and return the differences - Useful for comparing a DB with a DB that has been patched, can be used to generate changelogs
        differences = []
        for character in self.characters:
            diff = False
            if not db.has_character(character): # If the character is not in the other DB, add it to the differences list
                character['difference_reason'] = "Character not found in other DB"
                character["diff_type"] = "added_character"
                if character["ref_id"] is not None and character["ref_id"] in db.base_id_index:
                    character['difference_reason'] += " - same ref_id was found in other DB"
                    character["diff_type"] = "edited_character"
                if character["base_id"] is not None and character["base_id"] in db.base_id_index:
                    character['difference_reason'] += " - same base_id was found in other DB"
                    character["diff_type"] = "edited_character"
                diff = True
            else:
                character['differences'] = []
                character['diff_type'] = "edited_character"
                for key in character:
                    if key in db.named_index[character['name']]:
                        if str(character[key]) != str(db.named_index[character['name']][key]):
                            character['differences'].append({"key":key,"other":db.named_index[character['name']][key]})
                            diff = True
            if diff:
                differences.append(character)
        for character in db.characters:
            diff = False
            if not self.has_character(character):
                character['difference_reason'] = "New character found in other DB"
                if character["ref_id"] is not None and character["ref_id"] in self.base_id_index:
                    character['difference_reason'] += " - same ref_id was found in this DB"
                    character["diff_type"] = "edited_character"
                if character["base_id"] is not None and character["base_id"] in self.base_id_index:
                    character['difference_reason'] += " - same base_id was found in this DB"
                    character["diff_type"] = "edited_character"
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
        self.characters.sort(key=lambda x: x['name'])
        if type == 'json':
            if not os.path.exists(path):
                os.makedirs(path)
            for character in self.characters:
                json_file_path = os.path.join(path, str(self.config.game_id) + "_" + str(character['gender']) + "_" + str(character['race']) + "_" + str(character['name']) + "_" + str(character['ref_id']) + "_" + str(character['base_id']) + '.json')
                json.dump(character, open(json_file_path, 'w'), indent=4)
        elif type == 'csv':
            df = pd.DataFrame(self.characters)
            df.to_csv(path, index=False)
        else:
            logging.error(f"Could not save character database. Invalid type '{type}'.")
            raise ValueError
        
        
    @property
    def male_voice_models(self):
        valid = {}
        for character in self.characters:
            if character["gender"] == "Male" and "Female" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self.characters:
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
        for character in self.characters:
            if character["gender"] == "Female" and "Male" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self.characters:
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