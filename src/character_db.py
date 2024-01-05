import src.utils as utils
import src.tts as tts
import logging
import json
import os
import pandas as pd
import csv
class CharacterDB():
    def __init__(self, config, xvasynth=None): # character_df_directory is the path to a character directory where each character is a seperate json file
        self.config = config
        if xvasynth == None:
            xvasynth = tts.Synthesizer(config)
        self.xvasynth = xvasynth # xvasynth is the xvasynth synthesizer object
        self.character_df_path = config.character_df_file
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        self.valid = []
        self.invalid = []
        self.db_type = None
        # make sure voice_model_ref_ids_file exists
        if not os.path.exists(config.voice_model_ref_ids_file):
            logging.error(f"Could not find voice_model_ref_ids_file at {config.voice_model_ref_ids_file}. Please download the correct file for your game, or correct the filepath in your config.ini and try again.")
            raise FileNotFoundError
        if config.voice_model_ref_ids_file != "" and os.path.exists(config.voice_model_ref_ids_file):
            with open(config.voice_model_ref_ids_file, 'r') as f:
                self.voice_model_ids = json.load(f)
        else:
            self.voice_model_ids = {}
            
        print(f"Loading character database from {self.character_df_path}...")
        try:
            if self.character_df_path.endswith('.csv'):
                print("Loading character database from csv...")
                self.load_characters_csv()
            else:
                print("Loading character database from json...")
                self.load_characters_json()
            self.verify_characters()
        except:
            logging.error(f"Could not load character database from {self.character_df_path}. Please check the path and try again. Path should be a directory containing json files or a csv file containing character information.")
            raise

    def loaded(self):
        print(f"{len(self.male_voice_models)} Male voices - {len(self.female_voice_models)} Female voices")
        print("All Required Voice Models:",self.all_voice_models)
        print("Total Required Voice Models:",len(self.all_voice_models))
        print("voice_model_ids:",self.voice_model_ids)

    def load_characters_json(self):
        print(f"Loading character database from {self.character_df_path}...")
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        for file in os.listdir(self.character_df_path):
            if file.endswith(".json"):
                character = json.load(open(os.path.join(self.character_df_path, file)))
                self.characters.append(character)
                self.named_index[character['name']] = self.characters[-1]
                self.baseid_int_index[character['baseid_int']] = self.characters[-1]
        self.db_type = 'json'
        print(f"Loaded {len(self.characters)} characters from JSON {self.character_df_path}")
        self.loaded()
    
    def load_characters_csv(self):
        print(f"Loading character database from JSON files in {self.character_df_path}...")
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        encoding = utils.get_file_encoding(self.character_df_path)
        character_df = pd.read_csv(self.character_df_path, engine='python', encoding=encoding)
        character_df = character_df.loc[character_df['voice_model'].notna()]
        for _, row in character_df.iterrows():
            character = row.to_dict()
            self.characters.append(character)
            self.named_index[character['name']] = self.characters[-1]
            self.baseid_int_index[character['baseid_int']] = self.characters[-1]
        self.db_type = 'csv'
        print(f"Loaded {len(self.characters)} characters from csv {self.character_df_path}")
        self.loaded()

    def patch_character_info(self,info): # Patches information about a character into the character database and if db_type is json, saves the changes to the json file
        self.characters.append(info)
        self.named_index[info['name']] = self.characters[-1]
        self.baseid_int_index[info['baseid_int']] = self.characters[-1] 
        if self.db_type == 'json':
            if not os.path.exists(self.character_df_path): # If the directory doesn't exist, create it
                os.makedirs(self.character_df_path) 
            json_file_path = os.path.join(self.character_df_path, info['name']+'.json')
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
        # print(f"voice_model_ids: {voice_model}/{voice_model.replace(' ', '')}")
        folder = None
        for voice_folder in self.voice_folders:
            if voice_model == voice_folder:
                folder = self.voice_folders[voice_folder]
            if voice_model.replace(' ', '') == voice_folder:
                folder = self.voice_folders[voice_folder]
        # print(f"folder:",folder)
        if folder == None:
            folder = voice_model.replace(' ', '')
            print(f"Could not find voice folder for voice model '{voice_model}', defaulting to '{folder}'")
        if type(folder) == list:
            folder = folder[0]
        return folder
    
    def verify_characters(self):
        xvasynth_available_voices = self.xvasynth.voices()
        self.valid = []
        self.invalid = []
        self.unused_voices = []
        for voice in self.all_voice_models:
            voice_folder = self.get_voice_folder_by_voice_model(voice)
            if voice_folder in xvasynth_available_voices: # If the voice folder is available, add it to the valid list
                self.valid.append(voice_folder.replace(' ', ''))
            elif voice in self.voice_folders: # If the voice model is a valid voice folder, add it to the valid list
                self.valid.append(voice.replace(' ', ''))
            else:
                print(f"invalid voice: {voice_folder}")
                self.invalid.append(voice_folder)
                self.invalid.append(voice)
        for voice in xvasynth_available_voices:
            # add spaces before each capital letter
            spaced_voice = ""
            for letter in voice.replace(' ', ''):
                if letter.isupper():
                    spaced_voice += " "
                spaced_voice += letter
            if voice not in self.valid and voice.replace(' ', '') not in self.valid and spaced_voice not in self.valid:
                self.unused_voices.append(voice)
                print(f"unused voice: {voice}")
        for voice in self.unused_voices:
            for character in self.characters:
                if character['skyrim_voice_folder'] == voice or character['voice_model'] == voice:
                    print(f"Character '{character['name']}' uses unused voice model '{voice}'")
        print(f"Valid voices found in character database: {len(self.valid)}/{len(self.all_voice_models)}")

        print(f"Total unused voices: {len(self.unused_voices)}/{len(xvasynth_available_voices)}")
        if len(self.invalid) > 0:
            print(f"Invalid voices found in character database: {self.invalid}. Please check that the voices are installed and try again.")
            for character in self.characters:
                if character['voice_model'] in self.invalid:
                    if character['voice_model'] != "":
                        print(f"WARNING: Character '{character['name']}' uses invalid voice model '{character['voice_model']}'! This is an error, please report it!")
                        print("(The rest of the program will continue to run, but this character might not be able to be used)")

    def has_character(self, character, exact=False):
        character_in_db = False
        for db_character in self.characters:
            if exact:
                for key in character: # Check if the character is already in the database at every key
                    if key in db_character:
                        if str(character[key]) == str(db_character[key]):
                            character_in_db = True
                            break
            else:
                if character['name'] == db_character['name']:
                    character_in_db = True
                    break
        return character_in_db
    
    def compare(self,db): # Compare this DB with another DB and return the differences - Useful for comparing a DB with a DB that has been patched
        differences = []
        for character in self.characters:
            if not db.has_character(character):
                character['difference_reason'] = "Character not found in other DB"
                differences.append(character)
            elif not db.has_character(character, True):
                character['difference_reason'] = "Character found in other DB but with different information"
                differences.append(character)
        for character in db.characters:
            if not self.has_character(character):
                character['difference_reason'] = "Character not found in this DB"
                differences.append(character)
            elif not self.has_character(character, True):
                character['difference_reason'] = "Character found in this DB but with different information"
                differences.append(character)
        for folder in self.voice_folders:
            if folder not in db.voice_folders:
                differences.append({"voice_model":folder,"difference_reason":"Voice model not found in other DB"})
        for folder in db.voice_folders:
            if folder not in self.voice_folders:
                differences.append({"voice_model":folder,"difference_reason":"Voice model not found in this DB"})
        for voice_model in self.all_voice_models:
            if voice_model not in db.all_voice_models:
                differences.append({"voice_model":voice_model,"difference_reason":"Voice model not found in other DB"})
        for voice_model in db.all_voice_models:
            if voice_model not in self.all_voice_models:
                differences.append({"voice_model":voice_model,"difference_reason":"Voice model not found in this DB"})
        for unused_voice in db.unused_voices:
            if unused_voice not in self.unused_voices:
                related_characters = []
                for character in db.characters:
                    if character['skyrim_voice_folder'] == unused_voice or character['voice_model'] == unused_voice:
                        related_characters.append(character['name'])
                differences.append({"voice_model":unused_voice,"difference_reason":"Unused voice found in other DB","related_characters":related_characters})
        for unused_voice in self.unused_voices:
            if unused_voice not in db.unused_voices:
                related_characters = []
                for character in self.characters:
                    if character['skyrim_voice_folder'] == unused_voice or character['voice_model'] == unused_voice:
                        related_characters.append(character['name'])
                differences.append({"voice_model":unused_voice,"difference_reason":"Unused voice found in this DB","related_characters":related_characters})
        if len(self.characters) > len(db.characters):
            differences.append({"difference_reason":"This DB has more characters than the other DB (This is not necessarily an error, if there are not missing characters, this might mean that the original DB had duplicates that were automatically removed!)", "characters":len(self.characters), "db_characters":len(db.characters)})
        elif len(self.characters) < len(db.characters):
            differences.append({"difference_reason":"This DB has less characters than the other DB -- Honestly I don't know under what circumestance this could be possible, but if you see this error, please report it!", "characters":len(self.characters), "db_characters":len(db.characters)})
        return differences
    
    def save(self, path, type='json'): # Save the character database to a json directory or csv file
        self.characters.sort(key=lambda x: x['name'])
        if type == 'json':
            if not os.path.exists(path):
                os.makedirs(path)
            for character in self.characters:
                json_file_path = os.path.join(path, str(self.config.xvasynth_game_id) + "_" + str(character['gender']) + "_" + str(character['race']) + "_" + str(character['name']) + "_" + str(character['refid_int']) + "_" + str(character['baseid_int']) + '.json')
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