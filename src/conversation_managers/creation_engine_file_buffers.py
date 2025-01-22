print("Loading conversation_managers/creation_engine_file_buffers.py...")
from src.logging import logging, time
import src.characters_manager as characters_manager # Character Manager class
from src.conversation_managers.base_conversation_manager import BaseConversationManager
import src.utils as utils
import os
import random
import uuid
import json
import traceback
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
        self.conversation_started_radiant = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.radiant_dialogue = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_gender = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_race = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.current_location = 'Skyrim' # Initialised at start of every conversation in await_and_setup_conversation()
        logging.info(f"Creation Engine (File Buffer) Conversation Manager Initialized")
        if initialize:
            self.game_interface.write_game_info('_pantella_status', 'Started Pantella')
        
    def get_if_new_character_joined(self):
        """Check if new character has been added to conversation"""
        num_characters_selected = self.game_interface.load_ingame_actor_count()
        if num_characters_selected > self.character_manager.active_character_count():
            return True
        else:
            return False
        
    def setup_character(self, character_info):
        character = super().setup_character(character_info)
        self.game_interface.setup_voiceline_save_location(character_info['in_game_voice_model']) # if the NPC is from a mod, create the NPC's voice folder and exit Pantella
        return character

    def check_new_joiner(self):
        new_character_joined = self.get_if_new_character_joined() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        if new_character_joined: # if new character has joined the conversation or radiant dialogue is being used and there are more than one active characters, switch to Single Prompt Multi-NPC conversation
            try: # load character info, location and other gamestate data when data is available - Starts watching the _pantella_ files in the Skyrim folder and waits for the player to select an NPC
                character_info, self.current_location, self.current_in_game_time, self.player_name, player_race, player_gender, self.conversation_started_radiant = self.game_interface.load_game_state()
            except characters_manager.CharacterDoesNotExist as e:
                self.game_interface.write_game_info('_pantella_end_conversation', 'True') # End the conversation in game
                logging.info('Restarting...')
                logging.error(f"Error: {e}")
            logging.info(f"New character joined conversation: {character_info['name']}")

            try:
                character = self.setup_character(character_info)
            except Exception as e:
                self.game_interface.write_game_info('_pantella_end_conversation', 'True')
                self.conversation_ended = True

                logging.error(f"Error: {e}")
                tb = traceback.format_exc()
                logging.error(tb)
                if not self.config.continue_on_missing_character:
                    input("Press Enter to exit.")
                    raise e

            if len(self.messages) == 0: # At least only do this if the conversation hasn't started yet? Maybe? Let me know if this is a problem.
                greeting = random.choice(character.language['predetermined_npc_greetings'])
                self.new_message({"role": self.config.assistant_name, "name":character.name, "content": f"{greeting}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)?
                
            self.game_interface.write_game_info('_pantella_character_selection', 'True') # write to _pantella_character_selection.txt to indicate that the character has been successfully selected to the game

    def update_game_state(self):
        self.conversation_ended = self.game_interface.is_conversation_ended() # wait for the game to indicate that the conversation has ended or not
        self.radiant_dialogue = self.game_interface.is_radiant_dialogue() # check if radiant dialogue is being used
        self.check_new_joiner() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        self.game_interface.update_game_events() # update game events before player input
        self.current_location = self.game_interface.get_current_location() # update current location each step of the conversation
        self.current_in_game_time = self.game_interface.get_current_game_time() # update current in game time each step of the conversation
        if self.get_conversation_type() == 'single_player_with_npc': # TODO: Currently only available for single player with NPC conversations, will have to figure out how to make this work for multi NPC conversations later
            self.game_interface.active_character.update_game_state() # update game state for active character

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

    async def await_and_setup_conversation(self): # wait for player to select an NPC and setup the conversation when outside of conversation
        self.conversation_id = str(uuid.uuid4()) # Generate a unique ID for the conversation
        self.game_interface.reset_game_info() # clear _pantella_ files in Skyrim folder

        self.conversation_step += 1

        logging.info('Conversations not starting when you select an NPC? Post an issue on the GitHub page: https://github.com/Pathos14489/Pantella Or (if you want quick responses for any issues) the Discord: https://discord.gg/M7Zw8mBY6r')
        logging.info('Waiting for player to select an NPC...')
        
        try: # load character info, location and other gamestate data when data is available - Starts watching the _pantella_ files in the Skyrim folder and waits for the player to select an NPC
            character_info, self.current_location, self.current_in_game_time, self.player_name, self.player_race, self.player_gender, self.conversation_started_radiant = self.game_interface.load_game_state()
        except characters_manager.CharacterDoesNotExist as e:
            self.game_interface.write_game_info('_pantella_end_conversation', 'True') # End the conversation in game
            logging.info('Restarting...')
            logging.error(f"Error Loading Character<await_and_setup_conversation>: {e}")
        self.radiant_dialogue = self.conversation_started_radiant
        
        try:
            # setup the character that the player has selected
            character = self.setup_character(character_info)
        except Exception as e:
            self.game_interface.write_game_info('_pantella_end_conversation', 'True')
            self.conversation_ended = True
            logging.error(f"Error Setting Up Character<await_and_setup_conversation>: {e}")
            tb = traceback.format_exc()
            logging.error(tb)
            if not self.config.continue_on_missing_character:
                input("Press Enter to exit.")
                raise e
            return

        self.game_interface.write_game_info('_pantella_character_selection', 'True') # write to _pantella_character_selection.txt to indicate that the character has been selected to the game

        self.messages = [] # clear messages
        tokens_in_use = self.tokenizer.num_tokens_from_messages(self.get_context())
        self.tokens_available = self.config.maximum_local_tokens - tokens_in_use # calculate number of tokens available for the conversation
        logging.info(f"Tokens Available: {self.tokens_available}")
        logging.info(f"Tokens In Use: {tokens_in_use}")
        self.game_interface.update_game_events() # update game events before first player input
        prompt_style = self.character_manager.prompt_style # get prompt style from character manager
        if not self.radiant_dialogue: # initiate conversation with character
            try: # get response from NPC to player greeting
                self.new_message({'role': self.config.conversation_start_role, 'content': self.character_manager.language["intro_message"].replace("{name}",character.name)}) # TODO: Improve more later
                # Conversation Start Type Handling
                logging.config(f"Conversation Start Type: {self.config.conversation_start_type}")
                if self.config.conversation_start_type == "always_llm_choice":
                    await self.get_response()
                elif self.config.conversation_start_type == "always_force_npc_greeting":
                    await self.get_response(character)
                elif self.config.conversation_start_type == "always_player_greeting":
                    self.in_conversation = True
                    self.conversation_ended = False
                elif self.config.conversation_start_type == "implicit_predetermined_player_greeting":
                    greeting = random.choice(prompt_style["language"]["predetermined_player_greetings"])
                    greeting.replace("[character]", character.name)
                    self.new_message({'role': self.config.user_name, 'name':"[player]", 'content': greeting})
                    await self.get_response()
                elif self.config.conversation_start_type == "predetermined_npc_greeting":
                    greeting = random.choice(character.language['predetermined_npc_greetings'])
                    await character.say(greeting)
                    await self.get_response()
                elif self.config.conversation_start_type == "predetermined_npc_greeting_for_first_meeting_then_llm_choice":
                    if len(character.memory_manager.get_all_messages()) == 0:
                        greeting = random.choice(character.language['predetermined_npc_greetings'])
                        await character.say(greeting)
                    await self.get_response()
                elif self.config.conversation_start_type == "force_npc_greeting_for_first_meeting_then_llm_choice":
                    if len(character.memory_manager.get_all_messages()) == 0:
                        await self.get_response(character)
                    else:
                        await self.get_response()
                else:
                    raise Exception(f"Invalid conversation_start_type: {self.config.conversation_start_type}")
            except Exception as e: # if error, close Pantella
                self.game_interface.write_game_info('_pantella_end_conversation', 'True')
                logging.error(f"Error Getting Response in await_and_setup_conversation(): {e}")
                tb = traceback.format_exc()
                logging.error(tb)
                input("Press Enter to exit.")
                raise e
        else: # if radiant dialogue, get response from NPC to other NPCs greeting
            if len(self.messages) <= 2: # if radiant dialogue and the NPCs haven't greeted each other yet, greet each other
                if self.character_manager.active_character_count() == 2: # TODO: Radiants can only handle 2 NPCs at a time, is that normal?
                    greeting = random.choice(self.game_interface.active_character.language['predetermined_npc_greetings'])
                    self.new_message({'role': self.config.assistant_name, 'name':self.game_interface.active_character.name, 'content': greeting}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)
                else:
                    greeting = random.choice(self.game_interface.active_character.language['predetermined_npc_greetings'])
                    self.new_message({'role': self.config.assistant_name, 'name':self.game_interface.active_character.name, 'content': greeting}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)

        self.game_interface.update_game_events() # update game events before player input

        self.in_conversation = True
        self.conversation_ended = False

    async def step(self): # process player input and NPC response until conversation ends at each step of the conversation
        self.conversation_step += 1
        if self.in_conversation == False:
            logging.info('Cannot step through conversation when not in conversation')
            self.conversation_ended = True
            return
        generate_this_step = True
        
        self.update_game_state()

        if self.character_manager.active_character_count() == 1 and self.radiant_dialogue: # if radiant dialogue and only one NPC, skip stepping this conversation
            # logging.info("Radiant NPC waiting for other people to join the conversation, stepping...")
            time.sleep(0.2)
            return
        logging.info('Stepping through conversation...')
        logging.info(f"Messages: {json.dumps(self.get_loggable_context(), indent=2)}")
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
            # transcribed_text = self.transcriber.get_player_response(", ".join(self.character_manager.active_characters.keys()))
            transcribed_text = self.game_interface.get_player_response(self.character_manager.active_characters.keys())
            player_sent_message = False

            if transcribed_text == "EndConversationNow":
                self.end_conversation()
            elif transcribed_text == "ForgetLastMessage": # Forget the last message
                self.character_manager.forget_last_message()
                self.messages.pop() # remove last message from messages
                generate_this_step = False
                transcribed_text = ""
            elif transcribed_text == "RegenLastMessage": # Forget the last message and regenerate it
                self.character_manager.forget_last_message() 
                self.messages.pop() # remove last message from messages
                transcribed_text = ""
            else: # if player input is not empty, and isn't a special command, run player behaviors
                self.behavior_manager.run_player_behaviors(transcribed_text) # run player behaviors
                self.game_interface.write_game_info('_pantella_player_input', transcribed_text) # write player input to _pantella_player_input.txt
                self.new_message({'role': self.config.user_name, 'name':"[player]", 'content': transcribed_text}) # add player input to messages
                player_sent_message = True
                
            self.character_manager.before_step() # Let the characters know that a step has been taken
            self.update_game_state()
            
            if player_sent_message:
                # check if user is ending conversation
                transcript_cleaned = utils.clean_text(transcribed_text)
                end_convo = False
                for keyword in  self.character_manager.language["end_conversation_keywords"]:
                    if utils.activation_name_exists(transcript_cleaned, keyword):
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

        # if self.character_manager.active_character_count() == 1: # check if NPC is in combat to change their voice tone (if one on one conversation)
        #     # TODO: Make this work for multi NPC conversations
        #     aggro = self.game_interface.load_data_when_available('_pantella_actor_is_in_combat', '').lower() == 'true' # TODO: Make this a game_state_manager method instead of an inline call
        #     if aggro:
        #         self.game_interface.active_character.is_in_combat = 1
        #     else:
        #         self.game_interface.active_character.is_in_combat = 0

        
        if generate_this_step and ((transcribed_text is not None and transcribed_text != '') or (self.radiant_dialogue and self.character_manager.active_character_count() > 1)) and not self.conversation_ended and self.in_conversation: # if player input is not empty and conversation has not ended, get response from NPC
            await self.get_response()
        
        # if npc ended conversation
        if self.conversation_ended and self.in_conversation:
            self.end_conversation()

        self.character_manager.after_step() # Let the characters know that a step has been taken
        # if the conversation is becoming too long, save the conversation to memory and reload
        if self.tokenizer.num_tokens_from_messages(self.messages[1:]) > (round(self.tokens_available*self.config.conversation_limit_pct,0)): # if the conversation is becoming too long, save the conversation to memory and reload
            self.reload_conversation()