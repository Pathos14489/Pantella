import os
import asyncio
import logging
import pandas as pd
import src.game_state_manager as game_state_manager
import src.chat_manager as chat_manager
import src.characters_manager as characters_manager # Character Manager class
import src.behavior_manager as behavior_manager
import src.language_model as language_models
import src.tts as tts
import src.stt as stt
import src.utils as utils
import src.character_db as character_db

class conversation_manager():
    def __init__(self, config, initialize=True):
        self.config = config
        self.config.conversation_manager = self
        self.language_info = self.get_language_info()
        # self.config
        # self.language_info
        self.token_limit = self.config.maximum_local_tokens # Get token limit from config.json
        if self.config.ready:
            self.synthesizer = tts.create_Synthesizer(self) # Create Synthesizer object based on config - required by scripts for checking voice models, so is left out of self.initialize() intentionally
            self.character_database = character_db.CharacterDB(self) # Create Character Database Manager based on config - required by scripts for merging, patching and converting character databases, so is left out of self.initialize() intentionally
        self.mantella_version = '0.11-p'
        if initialize and self.config.ready:
            self.initialize()
            logging.info(f'\nMantella v{self.mantella_version}')
        self.character_manager = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.in_conversation = False # Whether or not the player is in a conversation
        self.conversation_ended = False # Whether or not the conversation has ended
        self.tokens_available = 0 # Initialised at start of every conversation in await_and_setup_conversation()
        self.current_location = 'Skyrim' # Initialised at start of every conversation in await_and_setup_conversation()
        if self.config.ready and self.game_state_manager is not None:
            self.current_in_game_time = self.game_state_manager.get_dummy_game_time() # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_name = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_gender = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_race = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.messages = [] # Initialised at start of every conversation in await_and_setup_conversation()
        self.conversation_started_radiant = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.radiant_dialogue = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.restart = False # Can be set at any time to force restart of conversation manager - Will ungracefully end any ongoing conversation client side
        self.conversation_step = 0 # The current step of the conversation - 0 is before any conversation has started, 1 is the first step of the conversation, etc.

    def get_conversation_type(self): # Returns the type of conversation as a string - none, single_npc_with_npc, single_player_with_npc, multi_npc
        if len(self.character_manager.active_characters) == 0:
            return 'none'
        elif len(self.character_manager.active_characters) == 1 and not self.radiant_dialogue:
            return 'single_player_with_npc'
        elif len(self.character_manager.active_characters) == 1 and self.radiant_dialogue:
            return 'single_npc_with_npc'
        else:
            return 'multi_npc'

    def get_language_info(self):
        language_df = pd.read_csv(self.config.language_support_file_path)
        try:
            language_info = language_df.loc[language_df['alpha2']==self.config.language].to_dict('records')[0]
            return language_info
        except:
            logging.error(f"Could not load language '{self.config.language}'. Please set a valid language in config.json\n")
            logging.error(f"Valid languages are: {', '.join(language_df['alpha2'].tolist())}")

    def initialize(self):
        self.llm, self.tokenizer = language_models.create_LLM(self) # Create LLM and Tokenizer based on config
        self.config.set_prompt_style(self.llm) # Set prompt based on LLM and config settings
        self.game_state_manager = game_state_manager.GameStateManager(self)
        self.chat_manager = chat_manager.ChatManager(self)
        self.transcriber = stt.Transcriber(self)
        self.behavior_manager = behavior_manager.BehaviorManager(self)

    def get_context(self): # Returns the current context(in the form of a list of messages) for the given active characters in the ongoing conversation
        system_prompt = self.character_manager.get_system_prompt()
        msgs = [{'role': self.config.system_name, 'content': system_prompt}]
        msgs.extend(self.messages) # add messages to context
        
        formatted_messages = [] # format messages to be sent to LLM - Replace [player] with player name appropriate for the type of conversation
        for msg in msgs: # Add player name to messages based on the type of conversation
            if msg['role'] == "[player]":
                if self.character_manager.active_character_count() > 1: # if multi NPC conversation use the player's actual name
                    formatted_messages.append({
                        'role': self.player_name,
                        'content': msg['content']
                    })
                else: # if single NPC conversation use the NPC's perspective player name
                    perspective_player_name, perspective_player_description, trust = self.chat_manager.active_character.get_perspective_player_identity()
                    formatted_messages.append({
                        'role': perspective_player_name,
                        'content': msg['content']
                    })
            else:
                formatted_messages.append(msg)
        return formatted_messages
        
    async def _get_response(self):
        sentence_queue = asyncio.Queue() # Create queue to hold sentences to be processed
        event = asyncio.Event() # Create event to signal when the response has been received
        event.set() # Set event to true to allow the first sentence to be processed

        await asyncio.gather(
            self.llm.process_response(sentence_queue, event),
            self.chat_manager.send_response(sentence_queue, event)
        )

    def get_response(self):
        """Get response from LLM and NPC(s) in the conversation"""
        return asyncio.run(self._get_response())

    def check_mcm_mic_status(self):
        """Check if the microphone is enabled in the MCM"""
        if os.path.exists(f'{self.config.game_path}/_mantella_microphone_enabled.txt'):
            with open(f'{self.config.game_path}/_mantella_microphone_enabled.txt', 'r', encoding='utf-8') as f:
                mcm_mic_enabled = f.readline().strip()
            return mcm_mic_enabled == 'TRUE'
        else:   
            return False

    def get_if_new_character_joined(self):
        """Check if new character has been added to conversation"""
        num_characters_selected = self.game_state_manager.load_ingame_actor_count()
        if num_characters_selected > self.character_manager.active_character_count():
            return True
        else:
            return False

    def setup_character(self,character_info, is_generic_npc):
        character = self.character_manager.get_character(character_info, is_generic_npc) # setup the character that the player has selectedc)
        self.synthesizer.change_voice(character)
        self.chat_manager.active_character = character
        self.chat_manager.character_num = 0
        self.character_manager.active_characters[character.name] = character # add new character to active characters
        self.chat_manager.setup_voiceline_save_location(character_info['in_game_voice_model']) # if the NPC is from a mod, create the NPC's voice folder and exit Mantella
        return character

    def check_new_joiner(self):
        new_character_joined = self.get_if_new_character_joined() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        if new_character_joined or (self.radiant_dialogue and self.character_manager.active_character_count() > 1): # if new character has joined the conversation or radiant dialogue is being used and there are more than one active characters, switch to Single Prompt Multi-NPC conversation
            try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
                character_info, self.current_location, self.current_in_game_time, is_generic_npc, self.player_name, player_race, player_gender, self.conversation_started_radiant = self.game_state_manager.load_game_state()
            except game_state_manager.CharacterDoesNotExist as e:
                self.game_state_manager.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
                logging.info('Restarting...')
                logging.error(f"Error: {e}")
            logging.info(f"New character joined conversation: {character_info['name']}")

            character = self.setup_character(character_info, is_generic_npc)

            # if not self.radiant_dialogue: # if not radiant dialogue format
            #     # add greeting from newly added NPC to help the LLM understand that this NPC has joined the conversation
            #     # messages_wo_system_prompt[self.last_assistant_idx]['content'] += f"\n{character.name}: self.{self.language_info['hello']}."
            self.messages.append({'role': character.name, 'content': f"{self.language_info['hello']}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)?
                
            self.game_state_manager.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been successfully selected to the game

    def get_response_from_input(self, author, input_text): # get response from input text
        self.get_response(author, input_text)

    def update_game_state(self):
        self.conversation_ended = self.game_state_manager.load_conversation_ended() # wait for the game to indicate that the conversation has ended or not
        self.radiant_dialogue = self.game_state_manager.load_radiant_dialogue() # check if radiant dialogue is being used
        self.check_new_joiner() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        self.game_state_manager.update_game_events() # update game events before player input
        self.current_location = self.game_state_manager.get_current_location() # update current location each step of the conversation
        self.current_in_game_time = self.game_state_manager.get_current_game_time() # update current in game time each step of the conversation

    def end_conversation(self, character=None): # end conversation with character
        if character is None and self.character_manager.active_character_count() > 0:
            character = self.chat_manager.active_character
        if character is not None:
            logging.info(f"Ending conversation with {character.name}")
            self.game_state_manager.end_conversation(character)
        if self.character_manager.active_character_count() <= 0:
            self.in_conversation = False
            self.conversation_ended = True
            self.conversation_step = 0 # reset conversation step count
            logging.info('Conversation ended')

    def await_and_setup_conversation(self): # wait for player to select an NPC and setup the conversation when outside of conversation
        self.game_state_manager.reset_game_info() # clear _mantella_ files in Skyrim folder

        self.character_manager = characters_manager.Characters(self) # Reset character manager
        self.transcriber.call_count = 0 # reset radiant back and forth count
        self.conversation_step += 1

        logging.info('\nConversations not starting when you select an NPC? Post an issue on the GitHub page: https://github.com/art-from-the-machine/Mantella')
        logging.info('\nWaiting for player to select an NPC...')
        try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
            character_info, self.current_location, self.current_in_game_time, is_generic_npc, self.player_name, self.player_race, self.player_gender, self.conversation_started_radiant = self.game_state_manager.load_game_state()
        except game_state_manager.CharacterDoesNotExist as e:
            self.game_state_manager.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
            logging.info('Restarting...')
            logging.error(f"Error Loading Character<await_and_setup_conversation>: {e}")
        self.radiant_dialogue = self.conversation_started_radiant
        
        # setup the character that the player has selected
        character = self.setup_character(character_info, is_generic_npc)
        
        self.game_state_manager.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been selected to the game

        self.messages = [] # clear messages

        self.tokens_available = self.token_limit - self.tokenizer.num_tokens_from_messages(self.get_context()) # calculate number of tokens available for the conversation

        self.game_state_manager.update_game_events() # update game events before first player input
        if not self.radiant_dialogue: # initiate conversation with character
            try: # get response from NPC to player greeting
                self.messages.append({'role': "[player]", 'content': f"{self.language_info['hello']} {character.name}."}) # TODO: Make this more interesting, always having the character say hi like we aren't always with each other is bizzare imo
                self.get_response()
            except Exception as e: # if error, close Mantella
                self.game_state_manager.write_game_info('_mantella_end_conversation', 'True')
                logging.error(f"Error Getting Response in await_and_setup_conversation(): {e}")
                input("Press Enter to exit.")
                raise e
        else: # if radiant dialogue, get response from NPC to other NPCs greeting
            if len(self.messages) <= 2: # if radiant dialogue and the NPCs haven't greeted each other yet, greet each other
                if self.character_manager.active_character_count() == 2: # TODO: Radiants can only handle 2 NPCs at a time, is that normal?
                    self.messages.append({'role': self.chat_manager.active_character.name, 'content': f"{self.language_info['hello']} {self.character_manager.active_characters[0].name}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)
                else:
                    self.messages.append({'role': self.chat_manager.active_character.name, 'content': f"{self.language_info['hello']}."}) # TODO: Make this more interesting by generating a greeting for each NPC based on the context of the last line or two said(or if possible check if they were nearby when the line was said...?)

        self.game_state_manager.update_game_events() # update game events before player input

        self.in_conversation = True
        self.conversation_ended = False

    def step(self): # process player input and NPC response until conversation ends at each step of the conversation
        self.conversation_step += 1
        if self.in_conversation == False:
            logging.info('Cannot step through conversation when not in conversation')
            self.conversation_ended = True
            return
        logging.info('Stepping through conversation...')
        logging.info(f"Messages: {self.messages}")
        
        self.update_game_state()

        if self.character_manager.active_character_count() == 1 and self.radiant_dialogue: # if radiant dialogue and only one NPC, skip stepping this conversation
            # logging.info("Radiant NPC waiting for other people to join the conversation, stepping...")
            return
        
        if (self.character_manager.active_character_count() <= 0) and not self.radiant_dialogue: # if there are no active characters in the conversation and radiant dialogue is not being used, end the conversation
            self.game_state_manager.end_conversation(self.chat_manager.active_character) # end conversation in game with current active character
            self.in_conversation = False
            return
        
        transcript_cleaned = ''
        transcribed_text = None
        if not self.conversation_ended and not self.radiant_dialogue: # check if conversation has ended and isn't radiant, if it's not, get next player input
            logging.info('Getting player response...')
            transcribed_text = self.transcriber.get_player_response()

            self.game_state_manager.write_game_info('_mantella_player_input', transcribed_text) # write player input to _mantella_player_input.txt

            transcript_cleaned = utils.clean_text(transcribed_text)

            self.messages.append({'role': "[player]", 'content': transcribed_text}) # add player input to messages
        
            self.update_game_state()

            # check if user is ending conversation
            if (self.transcriber.activation_name_exists(transcript_cleaned, self.config.end_conversation_keyword.lower())) or (self.transcriber.activation_name_exists(transcript_cleaned, 'good bye')) or (self.transcriber.activation_name_exists(transcript_cleaned, 'goodbye')) or self.conversation_ended:
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
                if not self.in_conversation: # if conversation has ended, stop stepping through conversation right now
                    return

        # Let the player know that they were heard
        #audio_file = synthesizer.synthesize(character.info['voice_model'], character.info['skyrim_voice_folder'], 'Beep boop. Let me think.')
        #chat_manager.save_files_to_voice_folders([audio_file, 'Beep boop. Let me think.'])

        if self.character_manager.active_character_count() == 1: # check if NPC is in combat to change their voice tone (if one on one conversation)
            # TODO: Make this work for multi NPC conversations
            aggro = self.game_state_manager.load_data_when_available('_mantella_actor_is_in_combat', '').lower() == 'true' # TODO: Make this a game_state_manager method instead of an inline call
            if aggro:
                self.chat_manager.active_character.is_in_combat = 1
            else:
                self.chat_manager.active_character.is_in_combat = 0

        
        if ((transcribed_text is not None and transcribed_text != '') or (self.radiant_dialogue and self.character_manager.active_character_count() > 1)) and not self.conversation_ended and self.in_conversation: # if player input is not empty and conversation has not ended, get response from NPC
            self.get_response()
        
        # if npc ended conversation
        if self.conversation_ended and self.in_conversation:
            self.end_conversation()
            return

        # if the conversation is becoming too long, save the conversation to memory and reload
        current_conversation_limit_pct = self.config.conversation_limit_pct # TODO: Make this a setting in the MCM
        if self.tokenizer.num_tokens_from_messages(self.messages[1:]) > (round(self.tokens_available*current_conversation_limit_pct,0)): # if the conversation is becoming too long, save the conversation to memory and reload
            self.game_state_manager.reload_conversation() # reload conversation - summarizing the conversation so far and starting a new abbreviated context using the summary to fill in the missing context
            if not self.conversation_ended and self.in_conversation: # if conversation has not ended, get response from NPC
                self.get_response() # get next response(s) from LLM after conversation is reloaded