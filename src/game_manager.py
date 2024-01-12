import logging
import src.utils as utils
import time
import random

class CharacterDoesNotExist(Exception):
    """Exception raised when NPC name cannot be found in characterDB"""
    pass


class GameStateManager:
    def __init__(self, game_path):
        self.game_path = game_path
        self.prev_game_time = ''


    def write_game_info(self, text_file_name, text):
        max_attempts = 2
        delay_between_attempts = 5

        for attempt in range(max_attempts):
            try:
                with open(f'{self.game_path}/{text_file_name}.txt', 'w', encoding='utf-8') as f:
                    f.write(text)
                break
            except PermissionError:
                print(f'Permission denied to write to {text_file_name}.txt. Retrying...')
                if attempt + 1 == max_attempts:
                    raise
                else:
                    time.sleep(delay_between_attempts)
        return None
    

    def load_data_when_available(self, text_file_name, text = ''):
        while text == '':
            with open(f'{self.game_path}/{text_file_name}.txt', 'r', encoding='utf-8') as f:
                text = f.readline().strip()
            # decrease stress on CPU while waiting for file to populate
            time.sleep(0.01)
        return text
    

    @utils.time_it
    def reset_game_info(self):
        self.write_game_info('_mantella_current_actor', '')
        character_name = ''

        self.write_game_info('_mantella_current_actor_id', '')
        character_id = ''

        self.write_game_info('_mantella_current_location', '')
        location = ''

        self.write_game_info('_mantella_in_game_time', '')
        in_game_time = ''

        self.write_game_info('_mantella_active_actors', '')

        self.write_game_info('_mantella_in_game_events', '')

        self.write_game_info('_mantella_status', 'False')

        self.write_game_info('_mantella_actor_is_enemy', 'False')

        self.write_game_info('_mantella_actor_is_in_combat', 'False')

        self.write_game_info('_mantella_actor_relationship', '')

        self.write_game_info('_mantella_character_selection', 'True')

        self.write_game_info('_mantella_say_line', 'False')
        self.write_game_info('_mantella_say_line_2', 'False')
        self.write_game_info('_mantella_say_line_3', 'False')
        self.write_game_info('_mantella_say_line_4', 'False')
        self.write_game_info('_mantella_say_line_5', 'False')
        self.write_game_info('_mantella_say_line_6', 'False')
        self.write_game_info('_mantella_say_line_7', 'False')
        self.write_game_info('_mantella_say_line_8', 'False')
        self.write_game_info('_mantella_say_line_9', 'False')
        self.write_game_info('_mantella_say_line_10', 'False')
        self.write_game_info('_mantella_actor_count', '0')

        self.write_game_info('_mantella_player_input', '')

        self.write_game_info('_mantella_aggro', '')

        self.write_game_info('_mantella_radiant_dialogue', 'False')
    
    
    def write_dummy_game_info(self, character_name):
        """Write fake data to game files when debugging"""

        self.write_game_info('_mantella_current_actor', character_name)

        character_id = '0'
        self.write_game_info('_mantella_current_actor_id', character_id)

        location = 'Skyrim'
        self.write_game_info('_mantella_current_location', location)
        
        in_game_time = '12'
        self.write_game_info('_mantella_in_game_time', in_game_time)

        return character_name, character_id, location, in_game_time
    

    def load_character_name_id(self):
        """Wait for character ID to populate then load character name"""

        character_id = self.load_data_when_available('_mantella_current_actor_id', '')
        time.sleep(0.5) # wait for file to register
        with open(f'{self.game_path}/_mantella_current_actor.txt', 'r') as f:
            character_name = f.readline().strip()
        
        return character_id, character_name
    
    def load_player_name(self):
        """Wait for player name to populate"""

        player_name = self.load_data_when_available('_mantella_player_name', '')
        return player_name
    
    def load_player_race(self):
        """Wait for player race to populate"""
        
        player_race = self.load_data_when_available('_mantella_player_race', '')
        player_race = player_race[0].upper() + player_race[1:].lower()
        return player_race
    
    def load_player_gender(self):
        """Wait for player gender to populate"""
        
        player_gender = self.load_data_when_available('_mantella_player_gender', '')
        return player_gender
    
    def load_radiant_dialogue(self):
        with open(f'{self.game_path}/_mantella_radiant_dialogue.txt', 'r', encoding='utf-8') as f: # check if radiant dialogue is enabled
            radiant_dialogue = f.readline().strip().lower()
        return radiant_dialogue == 'true'

    def load_conversation_ended(self):
        with open(f'{self.game_path}/_mantella_end_conversation.txt', 'r', encoding='utf-8') as f: # check if conversation has ended
            conversation_ended = f.readline().strip().lower()
        return conversation_ended == 'true'
    
    def load_ingame_actor_count(self):
        with open(f'{self.game_path}/_mantella_actor_count.txt', 'r', encoding='utf-8') as f: # check how many characters are in the conversation
            try:
                num_characters_selected = int(f.readline().strip())
            except:
                logging.info('Failed to read _mantella_actor_count.txt')
                num_characters_selected = 0
        return num_characters_selected
    
    def debugging_setup(self, debug_character_name):
        """Select character based on debugging parameters"""

        # None == in-game character chosen by spell
        if debug_character_name == 'None':
            character_id, character_name = self.load_character_name_id()
        else:
            character_name = debug_character_name
            debug_character_name = ''

        player_name = self.load_player_name()
        player_race = self.load_player_race()
        player_gender = self.load_player_gender()
        radiant_dialogue = self.load_radiant_dialogue() # get the radiant dialogue setting from _mantella_radiant_dialogue.txt

        character_name, character_id, location, in_game_time = self.write_dummy_game_info(character_name)

        return character_name, character_id, location, in_game_time, player_name, player_race, player_gender, radiant_dialogue
    
    
    def load_unnamed_npc(self, character_name, character_df):
        """Load generic NPC if character cannot be found in skyrim_characters.csv"""

        male_voice_models = character_df.male_voice_models
        female_voice_models = character_df.female_voice_models
        voice_model_ids = character_df.voice_model_ids

        actor_voice_model = self.load_data_when_available('_mantella_actor_voice', '')
        actor_voice_model_id = actor_voice_model.split('(')[1].split(')')[0]
        actor_voice_model_name = actor_voice_model.split('<')[1].split(' ')[0]

        actor_race = self.load_data_when_available('_mantella_actor_race', '')
        actor_race = actor_race.split('<')[1].split(' ')[0]

        actor_sex = self.load_data_when_available('_mantella_actor_sex', '')

        voice_model = ''
        for key in voice_model_ids:
            # using endswith because sometimes leading zeros are ignored
            if actor_voice_model_id.endswith(key):
                voice_model = voice_model_ids[key]
                break
        
        # if voice_model not found in the voice model ID list
        if voice_model == '':
            voice_model = character_df.get_character_by_voice_folder(actor_voice_model_name)["voice_model"] # return voice model from actor_voice_model_name
        else:    
            if actor_sex == '1':
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

        skyrim_voice_folder = character_df.get_voice_folder_by_voice_model(voice_model)
        
        character_info = {
            'name': character_name, # TODO: Generate random names for generic NPCs and figure out how to apply them in-game
            'bio': f'{character_name} is a {actor_race} {"Woman" if actor_sex=="1" else "Man"}.', # TODO: Generate more detailed background for generic NPCs
            'voice_model': voice_model,
            'skyrim_voice_folder': skyrim_voice_folder[0], # Default to the first for now, maybe change later?
        }

        # TODO: Enable this after adding random name generation to generic NPCs, otherwise all generic NPCs will share the same info I think
        # (Example: All Bandits would see themselves as Male Nord Bandits if the first Bandit you talked to was a Male Nord Bandit)
        # character_df.patch_character_info(character_info) # Add character info to skyrim_characters json directory if using json mode

        return character_info
    
    def get_current_location(self, presume = ''):
        location = self.load_data_when_available('_mantella_current_location', presume)
        if location.lower() == 'none' or location == "": # location returns none when out in the wild
            location = 'Skyrim'
        return location
    
    def get_current_game_time(self):
        in_game_time = self.load_data_when_available('_mantella_in_game_time', '')
        return int(in_game_time)
    
    @utils.time_it
    def load_game_state(self, config, character_df):
        """Load game variables from _mantella_ files in Skyrim folder (data passed by the Mantella spell)"""

        if config.debug_mode == '1':
            character_name, character_id, location, in_game_time, player_name, player_race, player_gender = self.debugging_setup(config.debug_character_name)
        else:
            location = self.get_current_location()
            in_game_time = self.get_current_game_time()
        
        # tell Skyrim papyrus script to start waiting for voiceline input
        self.write_game_info('_mantella_end_conversation', 'False')

        character_id, character_name = self.load_character_name_id()
        
        player_name = self.load_player_name()
        player_race = self.load_player_race()
        player_gender = self.load_player_gender()
        radiant_dialogue = self.load_radiant_dialogue() # get the radiant dialogue setting from _mantella_radiant_dialogue.txt

        try: # load character from skyrim_characters json directory
            character_info = character_df.named_index[character_name]
            is_generic_npc = False
        except KeyError: # character not found
            try: # try searching by ID
                logging.info(f"Could not find {character_name} in skyrim_characters.csv. Searching by ID {character_id}...")
                character_info = character_df.baseid_int_index[character_id]
                is_generic_npc = False
            except KeyError:
                logging.info(f"NPC '{character_name}' could not be found in 'skyrim_characters.csv'. If this is not a generic NPC, please ensure '{character_name}' exists in the CSV's 'name' column exactly as written here, and that there is a voice model associated with them.")
                character_info = self.load_unnamed_npc(character_name, character_df)
                is_generic_npc = True

        location = self.get_current_location(location) # Check if location has changed since last check

        in_game_time = self.get_current_game_time() # Check if in-game time has changed since last check

        actor_voice_model = self.load_data_when_available('_mantella_actor_voice', '')
        actor_voice_model_name = actor_voice_model.split('<')[1].split(' ')[0]
        character_info['in_game_voice_model'] = actor_voice_model_name

        actor_relationship_rank = self.load_data_when_available('_mantella_actor_relationship', '')
        try:
            actor_relationship_rank = int(actor_relationship_rank)
        except:
            actor_relationship_rank = 0
        character_info['in_game_relationship_level'] = actor_relationship_rank

        return character_info, location, in_game_time, is_generic_npc, player_name, player_race, player_gender, radiant_dialogue
    

    
    @utils.time_it
    def update_game_events(self, conversation_manager):
        """Add in-game events to player's response"""

        # append in-game events to player's response
        with open(f'{self.game_path}/_mantella_in_game_events.txt', 'r', encoding='utf-8') as f:
            in_game_events_lines = f.readlines()[-5:] # read latest 5 events

        # encapsulate events in {}
        formatted_in_game_events_lines = ['*{}*'.format(line.strip()) for line in in_game_events_lines]
        in_game_events = '\n'.join(formatted_in_game_events_lines)

        # Is Player in combat with NPC
        in_combat = self.load_data_when_available('_mantella_actor_is_enemy', '').lower() == 'true' 
        character = conversation_manager.chat_manager.active_character
        perspective_name, perspective_description, trust = character.get_perspective_player_identity()
        if in_combat:
            in_game_events = in_game_events + f'\n*{perspective_description} is fighting {character.name}. This is either because they are enemies or because {perspective_name} attacked {character.name} first.*'

        if len(in_game_events) > 0:
            logging.info(f'In-game events since previous exchange:\n{in_game_events}')

        # once the events are shared with the NPC, clear the file
        self.write_game_info('_mantella_in_game_events', '')

        # append the time to player's response
        in_game_time = self.get_current_game_time()
        
        # only pass the in-game time if it has changed
        if (in_game_time != self.prev_game_time) and (in_game_time != ''):
            self.prev_game_time = in_game_time
            time_group = utils.get_time_group(in_game_time)
            ampm = 'AM' if in_game_time < 12 else 'PM'
            twelve_hour_time = in_game_time if in_game_time <= 12 else in_game_time - 12

            time_string = f"The time is now {twelve_hour_time}:00 {ampm} {time_group}."
            logging.info(time_string)
            
            formatted_in_game_time = f"*{time_string}*\n"
            in_game_events = formatted_in_game_time + in_game_events
        
        if len(in_game_events.strip()) > 0:
            logging.info(f'In-game events since previous exchange:\n{in_game_events}')
            context = conversation_manager.messages.copy()
            last_message = context[-1]
            if last_message['role'] == conversation_manager.config.system_name:
                context[-1]['content'] += "\n" + in_game_events
            else:
                context += [{
                    "role": conversation_manager.config.system_name,
                    "content": in_game_events,
                }] # add in-game events to current ongoing conversation
        else:
            context = conversation_manager.messages

        return context
    
    
    @utils.time_it
    def end_conversation(self, conversation_ended, conversation_manager, tokenizer, synthesizer, chat_manager, messages, active_characters, tokens_available, character):
        """Say final goodbye lines and save conversation to memory"""

        # say goodbyes
        if not conversation_ended: # say line if NPC is not already deactivated
            latest_character = list(active_characters.items())[-1][1]
            audio_file = synthesizer.synthesize(latest_character, conversation_manager.config.goodbye_npc_response)
            chat_manager.save_files_to_voice_folders([audio_file, conversation_manager.config.goodbye_npc_response])

        perspective_name, _, _ = character.get_perspective_player_identity() # get perspective name - How the NPC refers to the player

        messages.append({"role": perspective_name, "content": conversation_manager.config.end_conversation_keyword+'.'})
        messages.append({"role": character.name, "content": conversation_manager.config.end_conversation_keyword+'.'})

        summary = None
        for character_name, character in active_characters.items(): # Get conversation summary from any character in the conversation or generate a new one
            if summary == None: # If summary has already been generated for another character in a multi NPC conversation (multi NPC memory summaries are shared)
                summary = character.save_conversation(tokenizer, messages, tokens_available, conversation_manager)
            else: # If summary has not been generated yet, generate it
                _ = character.save_conversation(tokenizer, messages, tokens_available, conversation_manager, summary)
        logging.info('Conversation ended.')

        self.write_game_info('_mantella_in_game_events', '') # clear in-game events
        self.write_game_info('_mantella_end_conversation', 'True') # tell Skyrim papyrus script conversation has ended
        time.sleep(conversation_manager.config.end_conversation_wait_time) # wait a few seconds for everything to register

        return None
    
    
    @utils.time_it
    def reload_conversation(self, conversation_manager, encoding, synthesizer, chat_manager, messages, active_characters, tokens_available, token_limit, location, in_game_time):
        """Restart conversation to save conversation to memory when token count is reaching its limit"""

        latest_character = list(active_characters.items())[-1][1]
        # let the player know that the conversation is reloading
        audio_file = synthesizer.synthesize(latest_character, conversation_manager.config.collecting_thoughts_npc_response)
        chat_manager.save_files_to_voice_folders([audio_file, conversation_manager.config.collecting_thoughts_npc_response])

        messages.append({"role": conversation_manager.config.user_name, "content": latest_character.info['name']+'?'}) # TODO: More robust way of returning to conversation, this is too limited
        if len(list(active_characters.items())) > 1:
            collecting_thoughts_response = latest_character.info['name']+': '+conversation_manager.config.collecting_thoughts_npc_response+'.'
        else:
            collecting_thoughts_response = conversation_manager.config.collecting_thoughts_npc_response+'.'
        messages.append({"role": conversation_manager.config.assistant_name, "content": collecting_thoughts_response})

        # save the conversation so far
        summary = None
        for character_name, character in active_characters.items():
            if summary == None:
                summary = character.save_conversation(encoding, messages, tokens_available, conversation_manager)
            else:
                _ = character.save_conversation(encoding, messages, tokens_available, conversation_manager, summary)
        # let the new file register on the system
        time.sleep(1)
        # if a new conversation summary file was created, load this latest file
        for character_name, character in active_characters.items():
            conversation_summary_file = character.get_latest_conversation_summary_file_path()

        # reload context
        keys = list(active_characters.keys())
        prompt = conversation_manager.config.prompt
        if len(keys) > 1:
            prompt = conversation_manager.config.multi_npc_prompt
        context = latest_character.set_context(prompt, location, in_game_time, active_characters, token_limit,"false")

        # add previous few back and forths from last conversation
        messages_wo_system_prompt = messages[1:]
        messages_last_entries = messages_wo_system_prompt[-8:]
        context.extend(messages_last_entries)

        return conversation_summary_file, context, messages
