print("Loading conversation_managers/creation_engine_file_buffers.py...")
from src.logging import logging, time
import src.characters_manager as characters_manager # Character Manager class
from src.conversation_managers.base_conversation_manager import BaseConversationManager
import src.utils as utils
import os
import uuid
import json
logging.info("Imported required libraries in conversation_managers/creation_engine_file_buffers.py")

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
manager_slug = "creation_engine_file_buffers"

class ConversationManager(BaseConversationManager):
    def __init__(self, config, initialize=True):
        super().__init__(config, initialize)
        print("Loading Creation Engine File Buffers Conversation Manager")
        self.current_in_game_time = None
        if initialize and self.config.ready:
            self.current_in_game_time = self.game_interface.get_dummy_game_time() # Initialised at start of every conversation in await_and_setup_conversation()
        self.character_manager = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.conversation_started_radiant = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.radiant_dialogue = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_gender = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_race = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.current_location = 'Skyrim' # Initialised at start of every conversation in await_and_setup_conversation()
        logging.info(f"Creation Engine (File Buffer) Conversation Manager Initialized")
        if initialize:
            self.game_interface.write_game_info('_mantella_status', 'Restarted Pantella')
        
    def get_conversation_type(self): # Returns the type of conversation as a string - none, single_npc_with_npc, single_player_with_npc, multi_npc
        if len(self.character_manager.active_characters) == 0:
            return 'none'
        elif len(self.character_manager.active_characters) == 1 and not self.radiant_dialogue:
            return 'single_player_with_npc'
        elif len(self.character_manager.active_characters) == 1 and self.radiant_dialogue:
            return 'single_npc_with_npc'
        else:
            return 'multi_npc'

    def get_if_new_character_joined(self):
        """Check if new character has been added to conversation"""
        num_characters_selected = self.game_interface.load_ingame_actor_count()
        if num_characters_selected > self.character_manager.active_character_count():
            return True
        else:
            return False
        
    def setup_character(self, character_info, is_generic_npc):
        character = super().setup_character(character_info, is_generic_npc)
        self.game_interface.setup_voiceline_save_location(character_info['in_game_voice_model']) # if the NPC is from a mod, create the NPC's voice folder and exit Mantella
        return character

    def check_new_joiner(self):
        new_character_joined = self.get_if_new_character_joined() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        if new_character_joined: # if new character has joined the conversation or radiant dialogue is being used and there are more than one active characters, switch to Single Prompt Multi-NPC conversation
            try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
                character_info, self.current_location, self.current_in_game_time, is_generic_npc, self.player_name, player_race, player_gender, self.conversation_started_radiant = self.game_interface.load_game_state()
            except characters_manager.CharacterDoesNotExist as e:
                self.game_interface.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
                logging.info('Restarting...')
                logging.error(f"Error: {e}")
            logging.info(f"New character joined conversation: {character_info['name']}")

            character = self.setup_character(character_info, is_generic_npc)

            # if not self.radiant_dialogue: # if not radiant dialogue format
            #     # add greeting from newly added NPC to help the LLM understand that this NPC has joined the conversation
            #     # messages_wo_system_prompt[self.last_assistant_idx]['content'] += f"\n{character.name}: self.{self.language_info['hello']}."
            if len(self.messages) == 0: # At least only do this if the conversation hasn't started yet? Maybe? Let me know if this is a problem.
                self.new_message({"role": self.config.assistant_name, "name":character.name, "content": f"{self.language_info['hello']}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)?
                
            self.game_interface.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been successfully selected to the game

    def update_game_state(self):
        self.conversation_ended = self.game_interface.is_conversation_ended() # wait for the game to indicate that the conversation has ended or not
        self.radiant_dialogue = self.game_interface.is_radiant_dialogue() # check if radiant dialogue is being used
        self.check_new_joiner() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        self.game_interface.update_game_events() # update game events before player input
        self.current_location = self.game_interface.get_current_location() # update current location each step of the conversation
        self.current_in_game_time = self.game_interface.get_current_game_time() # update current in game time each step of the conversation

    def end_conversation(self, character=None): # end conversation with character
        if character is None and self.character_manager.active_character_count() > 0:
            character = self.game_interface.active_character
        if character is not None:
            logging.info(f"Ending conversation with {character.name}")
            character.leave_conversation() # leave conversation in game with current active character
            self.game_interface.remove_from_conversation(character) # remove character from conversation in game
            self.character_manager.remove_from_conversation(character) # remove the character from the character manager
        if self.character_manager.active_character_count() <= 0:
            self.in_conversation = False
            self.conversation_ended = True
            self.conversation_step = 0 # reset conversation step count
            self.game_interface.end_conversation() # end conversation in game with current active character
            logging.info('Conversation ended')

    def await_and_setup_conversation(self): # wait for player to select an NPC and setup the conversation when outside of conversation
        self.conversation_id = str(uuid.uuid4()) # Generate a unique ID for the conversation
        self.game_interface.reset_game_info() # clear _mantella_ files in Skyrim folder

        self.character_manager = characters_manager.Characters(self) # Reset character manager
        self.transcriber.call_count = 0 # reset radiant back and forth count
        self.conversation_step += 1

        logging.info('\nConversations not starting when you select an NPC? Post an issue on the GitHub page: https://github.com/Pathos14489/Pantella')
        logging.info('\nWaiting for player to select an NPC...')
        
        try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
            character_info, self.current_location, self.current_in_game_time, is_generic_npc, self.player_name, self.player_race, self.player_gender, self.conversation_started_radiant = self.game_interface.load_game_state()
        except characters_manager.CharacterDoesNotExist as e:
            self.game_interface.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
            logging.info('Restarting...')
            logging.error(f"Error Loading Character<await_and_setup_conversation>: {e}")
        self.radiant_dialogue = self.conversation_started_radiant
        
        # setup the character that the player has selected
        character = self.setup_character(character_info, is_generic_npc)

        self.game_interface.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been selected to the game

        self.messages = [] # clear messages

        self.tokens_available = self.config.maximum_local_tokens - self.tokenizer.num_tokens_from_messages(self.get_context()) # calculate number of tokens available for the conversation

        self.game_interface.update_game_events() # update game events before first player input
        if not self.radiant_dialogue: # initiate conversation with character
            try: # get response from NPC to player greeting
                # self.new_message({'role': "[player]", 'content': f"{self.language_info['hello']} {character.name}."}) # TODO: Make this more interesting, always having the character say hi like we aren't always with each other is bizzare imo
                pp_name, _ = character.get_perspective_player_identity()
                self.new_message({'role': self.config.system_name, 'content': pp_name+" approaches "+character.name+" with the intent to start a new conversation with them."})
                self.get_response()
            except Exception as e: # if error, close Mantella
                self.game_interface.write_game_info('_mantella_end_conversation', 'True')
                logging.error(f"Error Getting Response in await_and_setup_conversation(): {e}")
                input("Press Enter to exit.")
                raise e
        else: # if radiant dialogue, get response from NPC to other NPCs greeting
            if len(self.messages) <= 2: # if radiant dialogue and the NPCs haven't greeted each other yet, greet each other
                if self.character_manager.active_character_count() == 2: # TODO: Radiants can only handle 2 NPCs at a time, is that normal?
                    self.new_message({'role': self.config.assistant_name, 'name':self.game_interface.active_character.name, 'content': f"{self.language_info['hello']} {self.character_manager.active_characters[0].name}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)
                else:
                    self.new_message({'role': self.config.assistant_name, 'name':self.game_interface.active_character.name, 'content': f"{self.language_info['hello']}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)

        self.game_interface.update_game_events() # update game events before player input

        self.in_conversation = True
        self.conversation_ended = False

    def step(self): # process player input and NPC response until conversation ends at each step of the conversation
        self.conversation_step += 1
        if self.in_conversation == False:
            logging.info('Cannot step through conversation when not in conversation')
            self.conversation_ended = True
            return
        
        self.update_game_state()

        if self.character_manager.active_character_count() == 1 and self.radiant_dialogue: # if radiant dialogue and only one NPC, skip stepping this conversation
            # logging.info("Radiant NPC waiting for other people to join the conversation, stepping...")
            return
        logging.info('Stepping through conversation...')
        logging.info(f"Messages: {json.dumps(self.get_context(), indent=2)}")
        # if self.llm.type == "chat":
        #     logging.info(f"Presumed Raw Prompt: {self.llm.tokenizer.get_string_from_messages(self.get_context())}")
        # elif self.llm.type == "normal":
        #     logging.info(f"Actual Raw Prompt: {self.llm.tokenizer.get_string_from_messages(self.get_context())}")
        
        if (self.character_manager.active_character_count() <= 0) and not self.radiant_dialogue: # if there are no active characters in the conversation and radiant dialogue is not being used, end the conversation
            self.end_conversation() # end conversation in game with current active character
        
        transcript_cleaned = ''
        transcribed_text = None
        if not self.conversation_ended and not self.radiant_dialogue: # check if conversation has ended and isn't radiant, if it's not, get next player input
            logging.info('Getting player response...')
            transcribed_text = self.transcriber.get_player_response(", ".join(self.character_manager.active_characters.keys()))
            if transcribed_text == "EndConversationNow":
                self.end_conversation()
            self.behavior_manager.run_player_behaviors(transcribed_text) # run player behaviors

            self.game_interface.write_game_info('_mantella_player_input', transcribed_text) # write player input to _mantella_player_input.txt

            transcript_cleaned = utils.clean_text(transcribed_text)

            self.new_message({'role': self.config.user_name, 'name':"[player]", 'content': transcribed_text}) # add player input to messages
            self.character_manager.before_step() # Let the characters know that a step has been taken
        
            self.update_game_state()

            # check if user is ending conversation
            end_convo = False
            for keyword in self.config.end_conversation_keywords:
                if self.transcriber.activation_name_exists(transcript_cleaned, keyword):
                    end_convo = True
                    break
            if end_convo or self.conversation_ended:
                # Detect who the player is talking to
                name_groups = []
                for character in self.character_manager.active_characters.values():
                    character_names = character.name.split(' ')
                    name_groups.append(character_names)
                all_words = transcript_cleaned.split(' ')
                goodbye_target_character = None
                for word in all_words: # check if any of the words in the player input match any of the names of the active characters, even partially. If so, end conversation with that character TODO: Make this a config setting "string" vs "partial" name_matching
                    for name_group in name_groups:
                        if word in name_group:
                            goodbye_target_character = self.character_manager.active_characters[' '.join(name_group)]
                            break
                self.end_conversation(goodbye_target_character) # end conversation in game with current active character, and if no active characters are left in the conversation, end it entirely

        if self.character_manager.active_character_count() == 1: # check if NPC is in combat to change their voice tone (if one on one conversation)
            # TODO: Make this work for multi NPC conversations
            aggro = self.game_interface.load_data_when_available('_mantella_actor_is_in_combat', '').lower() == 'true' # TODO: Make this a game_state_manager method instead of an inline call
            if aggro:
                self.game_interface.active_character.is_in_combat = 1
            else:
                self.game_interface.active_character.is_in_combat = 0

        
        if ((transcribed_text is not None and transcribed_text != '') or (self.radiant_dialogue and self.character_manager.active_character_count() > 1)) and not self.conversation_ended and self.in_conversation: # if player input is not empty and conversation has not ended, get response from NPC
            self.get_response()
        
        # if npc ended conversation
        if self.conversation_ended and self.in_conversation:
            self.end_conversation()

        self.character_manager.after_step() # Let the characters know that a step has been taken
        # if the conversation is becoming too long, save the conversation to memory and reload
        if self.tokenizer.num_tokens_from_messages(self.messages[1:]) > (round(self.tokens_available*self.config.conversation_limit_pct,0)): # if the conversation is becoming too long, save the conversation to memory and reload
            self.reload_conversation()