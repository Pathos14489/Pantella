import src.utils as utils
import logging
import json
import os
class CharacterDB():
    def __init__(self, config, xvasynth): # character_df_directory is the path to a character directory where each character is a seperate json file
        self.config = config
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
            logging.warning(f"Could not find voice folder for voice model '{voice_model}', defaulting to '{folder}'")
        return folder
    
    def verify_characters(self):
        xvasynth_available_voices = self.xvasynth.voices()
        self.valid = []
        self.invalid = []
        for voice in self.all_voice_models:
            voice_folder = self.get_voice_folder_by_voice_model(voice)
            if voice_folder in xvasynth_available_voices: # If the voice folder is available, add it to the valid list
                self.valid.append(voice_folder)
            elif voice in self.voice_folders: # If the voice model is a valid voice folder, add it to the valid list
                self.valid.append(voice)
            else:
                print(f"invalid voice: {voice} & {voice_folder}")
                self.invalid.append(voice)
                self.invalid.append(voice_folder)
        unused_voices = []
        for voice in xvasynth_available_voices:
            if voice not in self.valid:
                unused_voices.append(voice)
                print(f"unused voice: {voice}")
        print(f"Total unused voices: {len(unused_voices)}")
        if len(self.invalid) > 0:
            logging.warning(f"Invalid voices found in character database: {self.invalid}. Please check that the voices are installed and try again.")
            for character in self.characters:
                if character['voice_model'] in self.invalid:
                    if character['voice_model'] != "":
                        logging.warning(f"Character '{character['name']}' uses invalid voice model '{character['voice_model']}'")
        logging.info(f"Valid voices found in character database: {len(self.valid)}/{len(self.all_voice_models)}")
        
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
            race_string = character['race']+"Race"
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
            race_string = character['race']+"Race"
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