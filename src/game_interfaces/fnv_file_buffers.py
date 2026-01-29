print("Importing game_interfaces/fnv_file_buffers.py")
from src.logging import logging, time
from src.game_interfaces.creation_engine_file_buffers import GameInterface as CreationEngineFileBuffersInterface
import src.utils as utils
import os
import shutil
import sys
import asyncio
import json
from pydub import AudioSegment

def convert_wav_to_ogg(input_file, output_file):
    """
    Converts a WAV audio file to OGG format using pydub.
    
    Args:
        input_file (str): The path to the input .wav file.
        output_file (str): The path where the output .ogg file will be saved.
    """
    try:
        # Load the WAV file
        audio = AudioSegment.from_wav(input_file)
        
        # Export as OGG format (pydub automatically uses ffmpeg for the conversion)
        audio.export(output_file, format="ogg")
        
        print(f"Successfully converted '{input_file}' to '{output_file}'")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH.")
logging.info("Imported required libraries in game_interfaces/fnv_file_buffers.py")

valid_games = ["falloutnv"]
interface_slug = "fnv_file_buffers"

class GameInterface(CreationEngineFileBuffersInterface):
    def __init__(self,conversation_manager):
        super().__init__(conversation_manager, valid_games, interface_slug)
        logging.info("Loading Fallout: New Vegas file buffers game interface")
        # if not os.path.exists(f"{self.config.game_path}"):
        #     self.ready = False
        #     logging.error(f"Game path does not exist: {self.config.game_path}")
        # else:
        #     if not os.path.exists(self.config.game_path+'\\_pantella_fnv_folder.txt'):
        #         logging.warn(f'''Warning: Could not find _pantella_fnv_folder.txt in {self.config.game_path}.''')
        self.voice_id_map = self.load_voice_id_map()
        self.ogg_file = f'PantellaQu_PantellaDialogu_000010A1_1.ogg'
        self.lip_file = f'PantellaQu_PantellaDialogu_000010A1_1.lip'

    def load_voice_id_map(self):
        print(os.path.dirname(__file__))
        with open(os.path.join(os.path.dirname(__file__), "../../ttw_voice_id_map.json"), 'r', encoding='utf-8') as f:
            id_map = json.load(f)
        return id_map

    @utils.time_it
    def save_files_to_voice_folders(self, queue_output):
        """Save voicelines and subtitles to the correct game folders"""
        audio_file, subtitle = queue_output
        if audio_file is None or subtitle is None or audio_file == '' or subtitle == '':
            logging.error(f"Error saving voiceline to voice folders. Audio file: {audio_file}, subtitle: {subtitle}")
            return
        # logging.debug(f"Saving files to voice folders for character:", self.active_character.info)
        if self.config.linux_mode:
            ogg_file_path = f"{self.mod_voice_dir}/{self.active_character.info['in_game_voice_model']}/{self.ogg_file}"
            lip_file_path = f"{self.mod_voice_dir}/{self.active_character.info['in_game_voice_model']}/{self.lip_file}"
        else:
            ogg_file_path = f"{self.mod_voice_dir}\\{self.active_character.info['in_game_voice_model']}\\{self.ogg_file}"
            lip_file_path = f"{self.mod_voice_dir}\\{self.active_character.info['in_game_voice_model']}\\{self.lip_file}"
        if self.add_voicelines_to_all_voice_folders:
            logging.info(f"Adding voicelines to all voice folders")
            for sub_folder in os.scandir(self.mod_voice_dir):
                if sub_folder.is_dir():
                    #copy both the wav file and lip file if the game isn't Fallout4
                    out_path = f"{sub_folder.path}\\{self.ogg_file}"
                    if self.config.linux_mode:
                        out_path = f"{sub_folder.path}/{self.ogg_file}"
                    logging.info(f"Copying voiceline to {out_path}")
                    # shutil.copyfile(audio_file, out_path)
                    convert_wav_to_ogg(audio_file, out_path)
                    if self.config.linux_mode:
                        shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{sub_folder.path}/{self.lip_file}")
                    else:
                        shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{sub_folder.path}\\{self.lip_file}")
        else:
            logging.info(f"Converting and sending voiceline to {ogg_file_path}")
            # shutil.copyfile(audio_file, ogg_file_path)
            convert_wav_to_ogg(audio_file, ogg_file_path)
            logging.info(f"Copying lip file to {lip_file_path}")
            try:
                shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{lip_file_path}")
            except:
                print("Error copying lip file -- falling back to default lip file")
                default_lip_file = utils.resolve_path()+'/data/default.lip'
                shutil.copyfile(default_lip_file, f"{lip_file_path}")

        logging.info(f"{self.active_character.name} should speak")
        actor_number = self.active_character.info['actor_number']
        say_line_file = '_pantella_say_line_'+str(actor_number)
        logging.info(f"Voiceline File Buffer: _pantella_say_line_{actor_number}")
        self.write_game_info(say_line_file, subtitle.strip())
        
    @property
    def mod_voice_dir(self):
        if self.config.linux_mode:
            return f"{self.mod_path}/Sound/Voice/PantellaNV.esm"
        else:
            return f"{self.mod_path}\\Sound\\Voice\\PantellaNV.esm"

    # Needs work  
    @utils.time_it
    def reset_game_info(self):
        # PantellaAddActorToConversation
        self.write_game_info('_pantella_text_input', '')
        self.write_game_info('_pantella_in_game_events', '')
        self.write_game_info('_pantella_actor_voice', '')
        self.write_game_info('_pantella_current_actor', '')
        self.write_game_info('_pantella_current_actor_ref_id', '')
        self.write_game_info('_pantella_current_actor_base_id', '')
        self.write_game_info('_pantella_current_actor_race', '')
        self.write_game_info('_pantella_current_actor_gender', '')
        self.write_game_info('_pantella_current_actors', '')

        # PantellaRepository
        self.write_game_info('_pantella_text_input_enabled', 'False')
        self.write_game_info('_pantella_player_name', '')
        self.write_game_info('_pantella_player_race', '')
        self.write_game_info('_pantella_player_sex', '')
        self.write_game_info('_pantella_actor_count', '0')
        self.write_game_info('_pantella_character_selection', 'True')
        self.write_game_info('_pantella_end_conversation', 'False')
        self.write_game_info('_pantella_status', 'False')
        self.write_game_info('_pantella_say_line_1', 'False')

        # PantellaUpdate
        self.write_game_info('_pantella_player_is_starter', '')
        self.write_game_info('_pantella_player_teammate_count', '')

        self.write_game_info('_pantella_current_location', '')
        self.write_game_info('_pantella_starter_light_level', '')
        self.write_game_info('_pantella_starter_in_combat', '')
        self.write_game_info('_pantella_starter_trespassing', '')
        self.write_game_info('_pantella_starter_alerted', '')
        self.write_game_info('_pantella_starter_detected', '')
        self.write_game_info('_pantella_starter_is_cannibalizing_someone', '')
        self.write_game_info('_pantella_starter_was_attacked', '')
        self.write_game_info('_pantella_starter_alarmed', '')
        self.write_game_info('_pantella_starter_age_class', '')
        self.write_game_info('_pantella_starter_height', '')
        self.write_game_info('_pantella_starter_weight', '')
        self.write_game_info('_pantella_starter_radiation_level', '')
        self.write_game_info('_pantella_starter_sitting', '')
        self.write_game_info('_pantella_starter_sleeping', '')

        self.write_game_info('_pantella_are_in_combat', '')
        self.write_game_info('_pantella_relationship_rank', '')

        self.write_game_info('_pantella_target_light_level', '')
        self.write_game_info('_pantella_target_trespassing', '')
        self.write_game_info('_pantella_target_in_combat', '')
        self.write_game_info('_pantella_target_unconscious', '')
        self.write_game_info('_pantella_target_intimidated', '')
        self.write_game_info('_pantella_target_alerted', '')
        self.write_game_info('_pantella_target_is_teammate', '')
        self.write_game_info('_pantella_target_detected', '')
        self.write_game_info('_pantella_target_was_attacked', '')
        self.write_game_info('_pantella_target_alarmed', '')
        self.write_game_info('_pantella_target_age_class', '')
        self.write_game_info('_pantella_target_height', '')
        self.write_game_info('_pantella_target_weight', '')
        self.write_game_info('_pantella_target_radiation_level', '')
        self.write_game_info('_pantella_target_sitting', '')
        self.write_game_info('_pantella_target_sleeping', '')

        self.write_game_info('_pantella_current_time', '')
        self.write_game_info('_pantella_day_of_week', '')
        self.write_game_info('_pantella_moon_phase', '')
        self.write_game_info('_pantella_player_karma', '')

        self.write_game_info('_pantella_microphone_enabled', 'False')
        self.write_game_info('_pantella_context_string', '')
        self.write_game_info('_pantella_removed_from_conversation', '')
        # self.write_game_info('xxx', '')
        
    def get_current_game_time(self):
        """Return the current in-game time"""
        logging.info(f"Waiting for in-game time to populate...")
        in_game_time = self.load_data_when_available('_pantella_current_time', '') # Example: 07/12/0713 10:31
        in_game_chunks = in_game_time.split(' ')
        
        date = in_game_chunks[0] # Example: 07/12/0713
        date_chunks = date.split('/')
        month = int(date_chunks[0])
        day = int(date_chunks[1])
        year = int(date_chunks[2])

        time24 = in_game_chunks[1] # Example: 10:31
        time_chunks = time24.split(':')
        hour24 = int(time_chunks[0]) # 24 hour time
        hour12 = hour24 if hour24 <= 12 else hour24 - 12 # 12 hour time
        ampm = 'AM' if hour24 < 12 else 'PM' # AM or PM
        minute = int(time_chunks[1])
        time12 = f'{hour12}:{minute:02} {ampm}' # Example: 10:31 AM

        
        return {
            'year': year, # The current year in-game
            'month': month, # The current month in-game
            'day': day, # The current day in-game
            'hour24': hour24, # The current hour in-game in 24 hour time
            'hour12': hour12, # The current hour in-game in 12 hour time
            'minute': minute, # The current minute in-game
            'time24': time24, # The current time in-game in 24 hour time format (Example: 13:31)
            'time12': time12, # The current time in-game in 12 hour time format (Example: 1:31 PM)
            'ampm': ampm, # AM or PM
        }
    
    def load_character(self):
        """Wait for character ID to populate then load character name"""
        logging.info('Waiting for character base ID to populate...')
        character_base_id = self.load_data_when_available('_pantella_current_actor_base_id')
        logging.info('Got character base ID: '+character_base_id)
        logging.info('Waiting for character ref ID to populate...')
        character_ref_id = self.load_data_when_available('_pantella_current_actor_ref_id')
        logging.info('Got character ref ID: '+character_ref_id)
        logging.info('Waiting for character name to populate...')
        character_name = self.load_data_when_available('_pantella_current_actor')
        logging.info('Got character name: '+character_name)
        logging.info('Waiting for character race to populate...')
        character_race = self.load_data_when_available('_pantella_current_actor_race')
        logging.info('Got character race: '+character_race)
        logging.info('Waiting for character gender to populate...')
        character_gender = self.load_data_when_available('_pantella_current_actor_gender')
        logging.info('Got character gender: '+character_gender)
        logging.info('Waiting for character is_guard to populate...')
        is_guard = self.load_data_when_available('_pantella_actor_is_guard', 'False')
        logging.info('Got character is_guard: '+is_guard)
        logging.info('Waiting for character is_ghost to populate...')
        is_ghost = self.load_data_when_available('_pantella_actor_is_ghost', 'False')
        logging.info('Got character is_ghost: '+is_ghost)
        logging.info('Waiting for actor count to populate...')
        _pantella_actor_count = self.load_data_when_available('_pantella_actor_count')
        logging.info('Got actor count: '+_pantella_actor_count)
        # if (character_base_id == '0' and character_ref_id == '0') or (character_base_id == '' and character_ref_id == ''): # if character ID is 0 or empty, check old id file for refid
        #     with open(f'{self.game_path}\\_pantella_current_actor_id.txt', 'r') as f:
        #         character_id = f.readline().strip()
        #     character_ref_id = character_id
        #     character_base_id = None # No base ID available
        # time.sleep(0.5) # wait for file to register
        # with open(f'{self.game_path}\\_pantella_current_actor.txt', 'r') as f:
        #     character_name = f.readline().strip()
        
        return character_name, character_ref_id, character_base_id, character_race, character_gender, is_guard, is_ghost, _pantella_actor_count
    
    def load_player_name(self):
        """Wait for player name to populate"""
        logging.info('Waiting for player name to populate...')
        player_name = self.load_data_when_available('_pantella_player_name', '')
        logging.info('Got player name: '+player_name)
        return player_name
    
    def load_player_race(self):
        """Wait for player race to populate"""
        logging.info('Waiting for player race to populate...')
        player_race = self.load_data_when_available('_pantella_player_race', '')
        logging.info('Got player race: '+player_race)
        player_race = player_race[0].upper() + player_race[1:].lower()
        return player_race
    
    def load_player_gender(self):
        """Wait for player gender to populate"""
        logging.info('Waiting for player gender to populate...')
        player_gender = self.load_data_when_available('_pantella_player_sex', '')
        logging.info('Got player gender: '+player_gender)
        return player_gender
    
    def load_unnamed_npc(self, character_name):
        """Load generic NPC if character cannot be found in character database"""

        male_voice_models = self.conversation_manager.character_database.male_voice_models
        female_voice_models = self.conversation_manager.character_database.female_voice_models
        voice_model_ids = self.conversation_manager.character_database.voice_model_ids

        # actor_voice_model = self.load_data_when_available('_pantella_actor_voice', '')
        # actor_voice_model_id = actor_voice_model.split('(')[1].split(')')[0]
        # actor_voice_model_name = actor_voice_model.split('<')[1].split(' ')[0]
        actor_voice_model_id, actor_voice_model_name = self.load_actor_voice_model()

        actor_race = self.load_data_when_available('_pantella_actor_race', '')
        actor_race = actor_race.split('<')[1].split(' ')[0]

        actor_sex = self.load_data_when_available('_pantella_actor_gender', '')

        voice_model = ''
        for key in voice_model_ids:
            # using endswith because sometimes leading zeros are ignored
            if actor_voice_model_id.endswith(key):
                voice_model = voice_model_ids[key]
                break
        
        # if voice_model not found in the voice model ID list
        if voice_model == '':
            voice_model = self.conversation_manager.character_database.get_character_by_voice_folder(actor_voice_model_name)["voice_model"] # return voice model from actor_voice_model_name
        else:    
            if actor_sex == 'Female':
                try:
                    # voice_model = random.choice(female_voice_models[actor_race]) # Get random voice model from list of generic female voice models
                    # TODO: Enable this after adding random name generation to generic NPCs, otherwise all generic NPCs will share the same info I think
                    voice_model = female_voice_models[actor_race+ "Race"][0] # Default to the first for now, change later
                except:
                    voice_model = 'Female '+actor_race # Default to Same Sex Racial Equivalent
            else:
                try: 
                    # voice_model = random.choice(male_voice_models[actor_race]) # Get random voice model from list of generic male voice models
                    # TODO: Enable this after adding random name generation to generic NPCs, otherwise all generic NPCs will share the same info I think
                    voice_model = male_voice_models[actor_race+ "Race"][0] # Default to the first for now, change later
                except:
                    voice_model = 'Male '+actor_race # Default to Same Sex Racial Equivalent

        voice_folder = self.conversation_manager.character_database.get_voice_folder_by_voice_model(voice_model)
        
        character_info = {
            'name': character_name, # TODO: Generate random names for generic NPCs and figure out how to apply them in-game
            'bio': f'{character_name} is a {actor_race} {"Woman" if actor_sex=="1" else "Man"}.', # TODO: Generate more detailed background for generic NPCs
            "gender":{"Female" if actor_sex=="1" else "Male"},
            "race":actor_race,
            'voice_model': voice_model,
            'voice_folder': voice_folder[0], # Default to the first for now, maybe change later?
        }

        # TODO: Enable this after adding random name generation to generic NPCs, otherwise all generic NPCs will share the same info I think
        # (Example: All Bandits would see themselves as Male Nord Bandits if the first Bandit you talked to was a Male Nord Bandit)
        # character_database.patch_character_info(character_info) # Add character info to skyrim_characters json directory if using json mode

        return character_info
    
    def get_current_location(self, presume = ''):
        """Return the current location"""
        logging.info(f"Waiting for location to populate...")
        location = self.load_data_when_available('_pantella_current_location', presume)
        if location.lower() == 'none' or location == "": # location returns none when out in the wild
            location = 'Mojave Wasteland'
        return location
    
    @utils.time_it
    def update_game_events(self):
        """Add in-game events to player's response"""

        # append in-game events to player's response
        game_events_path = f'{self.game_path}\\_pantella_in_game_events.txt'
        if self.config.linux_mode:
            game_events_path = game_events_path.replace("\\", "/")
        with open(game_events_path, 'r', encoding='utf-8') as f:
            if self.config.game_update_pruning:
                in_game_events_lines = f.readlines()[-self.config.game_update_prune_count:] # read latest 5 events
            else:
                in_game_events_lines = f.readlines()
        
        in_game_events_lines = [line.strip() for line in in_game_events_lines]
        new_in_game_events = []
        for in_game_events_line in in_game_events_lines:
            new_line = in_game_events_line.replace("*","")
            while "*" in new_line:
                new_line = new_line.replace("*","")
            new_in_game_events.append(new_line)
        in_game_events_lines = [line for line in new_in_game_events if line.strip() != '']
        
        # Is Player in combat with NPC
        in_combat = self.load_data_when_available('_pantella_are_in_combat', '').lower() == 'true' 
        if in_combat:
            in_game_events_lines.append(self.conversation_manager.character_manager.language["game_events"]["player_started_combat"].format(name=self.active_character.name))
        self.new_game_events.extend(in_game_events_lines)
        
        super().update_game_events(False)

    def is_radiant_dialogue(self):
        """Check if radiant dialogue is enabled"""
        return False

    @utils.time_it
    def load_game_state(self):
        """Load game variables from _pantella_ files in Skyrim folder (data passed by the Pantella spell)"""

        location = self.get_current_location()
        logging.info(f"Current location: {location}")
        in_game_time = self.get_current_game_time()
        logging.info(f"Current in-game time: {in_game_time['time12']}")
        character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, _pantella_actor_count = self.load_character() # get the character's name and id from _pantella_current_actor.txt and _pantella_current_actor_id.txt
        player_name = self.load_player_name() # get the player's name from _pantella_player_name.txt
        player_race = self.load_player_race() # get the player's race from _pantella_player_race.txt
        player_gender = self.load_player_gender() # get player's gender from _pantella_player_sex.txt
        radiant_dialogue = self.is_radiant_dialogue() # get the radiant dialogue setting from _pantella_radiant_dialogue.txt    
        # tell Skyrim papyrus script to start waiting for voiceline input
        self.write_game_info('_pantella_end_conversation', 'False')

        
        actor_voice_model_id, actor_voice_model_name = self.load_actor_voice_model()
            # actor_voice_model = self.load_data_when_available('_pantella_actor_voice', '')
            # actor_voice_model_name = actor_voice_model.split('<')[1].split(' ')[0]
        logging.info(f"Actor voice model: {actor_voice_model_name}, Actor voice model ID: {actor_voice_model_id}")

        location = self.get_current_location(location) # Check if location has changed since last check

        character_info, _ = self.conversation_manager.character_database.get_character(character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, in_game_voice_model=actor_voice_model_name, location=location) # get character info from character database
        # TODO: Improve character lookup to be more accurate and to include generating character stats inspired by their generic name for generic NPCs instead of leaving them generic.
        # (example: make a backstory for a Bandit because the NPC was named Bandit, then generate a real name, and background inspired by that vague name for use in-corversation)
        # try: # load character from skyrim_characters json directory 
        #     character_info = self.conversation_manager.character_database.named_index[character_name]
        #     logging.info(f"Found {character_name} in character database as a named NPC: {character_info['name']}")
        # except KeyError: # character not found
        #     try: # try searching by ID
        #         logging.info(f"Could not find {character_name} in character database. Searching by ID {character_id}...")
        #         character_info = self.conversation_manager.character_database.baseid_int_index[character_id]
        #     except KeyError:
        #         logging.info(f"NPC '{character_name}' could not be found in character database. If this is not a generic NPC, please ensure '{character_name}' exists in the CSV's 'name' column exactly as written here, and that there is a voice model associated with them.")
        #         character_info = self.load_unnamed_npc(character_name)
        if character_info == None:
            logging.error(f"Character {character_name} not found in character database.")
            if self.config.continue_on_missing_character:
                logging.warn(f"Character {character_name} not found in character database. Create a new character for them, use a character generation enabled LLM, or set continue_on_missing_character to False in the config.")
                character_info = self.load_unnamed_npc(character_name)
            else:
                raise ValueError(f"Character {character_name} not found in character database.")


        in_game_time = self.get_current_game_time() # Check if in-game time has changed since last check

        if "voice_model" not in character_info or character_info["voice_model"].strip() == "":
            logging.info(f"Setting voice model for {character_name} to actor voice model: {actor_voice_model_name}")
            character_info['voice_model'] = actor_voice_model_name
        if "voice_folder" not in character_info or character_info["voice_folder"].strip() == "":
            voice_folder = self.conversation_manager.character_database.get_voice_folder_by_voice_model(character_info['voice_model'])
            character_info['voice_folder'] = voice_folder[0] # Default to the first for now, maybe change later?
            logging.info(f"Setting voice folder for {character_name} to {character_info['voice_folder']} based on voice model {character_info['voice_model']}")
        character_info['in_game_voice_model'] = actor_voice_model_name
        character_info['refid_int'] = character_ref_id
        if (character_ref_id is not None and character_ref_id != "0" and character_ref_id != "") and ("ref_id" not in character_info or character_info["ref_id"].strip() == ""):
            character_info["ref_id"] = str(hex(int(character_ref_id)))[2:]
        character_info['baseid_int'] = character_base_id
        if (character_base_id is not None and character_base_id != "0" and character_base_id != "") and ("base_id" not in character_info or character_info["base_id"].strip() == ""):
            character_info["base_id"] = str(hex(int(character_base_id)))[2:]
        character_info["in_game_race"] = character_in_game_race
        character_info["in_game_gender"] = character_in_game_gender
        # character_info["is_guard"] = character_is_guard
        # character_info["is_ghost"] = character_is_ghost
        character_info["actor_number"] = _pantella_actor_count
        character_info['character_name'] = character_name
        character_info['in_game_voice_model_id'] = actor_voice_model_id
        if "name" not in character_info or character_info["name"].strip() == "":
            character_info["name"] = character_name
        if "race" not in character_info or character_info["race"].strip() == "":
            character_info["race"] = character_in_game_race
        if "gender" not in character_info or character_info["gender"].strip() == "":
            character_info["gender"] = character_in_game_gender


        # actor_relationship_rank = self.load_data_when_available('_pantella_actor_relationship', '')
        # try:
        #     actor_relationship_rank = int(actor_relationship_rank)
        # except:
        #     logging.warn(f'Failed to read actor relationship rank from _pantella_actor_relationship.txt')
        actor_relationship_rank = 0
        logging.info(f'Actor relationship rank set to {actor_relationship_rank}')
        character_info['in_game_relationship_level'] = actor_relationship_rank

        return character_info, location, in_game_time, player_name, player_race, player_gender, radiant_dialogue