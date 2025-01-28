print("Loading conversation_managers/creation_engine_file_buffers.py...")
from src.logging import logging
from src.conversation_managers.base_conversation_manager import BaseConversationManager
import src.utils as utils
import json
import traceback
import uuid
import src.characters_manager as characters_manager # Character Manager class
logging.info("Imported required libraries in conversation_managers/creation_engine_file_buffers.py")

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
manager_slug = "gradio"

class ConversationManager(BaseConversationManager):
    def __init__(self, config, initialize=True):
        super().__init__(config, initialize)
        self.current_in_game_time_block = None
        self.character_manager = None # Initialised at start of the debug_ui.py script
        self.current_location = None # Initialised at start of the debug_ui.py script
        self.gr_blocks = None # Initialised at start of the debug_ui.py script
        self.title_label = None # Initialised at start of the debug_ui.py script
        self.npc_selector = None # Initialised at start of the debug_ui.py script
        self.npc_add_button = None # Initialised at start of the debug_ui.py script
        self.chat_box = None # Initialised at start of the debug_ui.py script
        self.chat_input = None # Initialised at start of the debug_ui.py script
        self.retry_button = None # Initialised at start of the debug_ui.py script
        self.latest_voice_line = None # Initialised at start of the debug_ui.py script
        self.radiant_dialogue = False
        logging.info(f"Gradio Conversation Manager Initialized")
        
    # @property
    # def player_name(self):
    #     return self.player_name_block.value
    
    # @property
    # def player_race(self):
    #     return self.player_race_block.value
    
    # @property
    # def player_sex(self):
    #     return self.player_sex_block.value
        
    def assign_gradio_blocks(self, gr_blocks, title_label, npc_selector, current_location, player_name_block, player_race_block, player_gender_block, npc_add_button, chat_box, chat_input, retry_button, latest_voice_line):
        self.gr_blocks = gr_blocks
        self.title_label = title_label
        self.npc_selector = npc_selector
        self.current_location = current_location
        self.player_name_block = player_name_block
        self.player_name = self.game_interface.player_name
        self.player_race_block = player_race_block
        self.player_race = self.game_interface.player_race
        self.player_gender_block = player_gender_block
        self.player_gender = self.game_interface.player_gender
        self.npc_add_button = npc_add_button
        self.chat_box = chat_box
        self.chat_input = chat_input
        self.retry_button = retry_button
        self.latest_voice_line = latest_voice_line
        self.npc_add_button.click(self.game_interface.set_game_state, inputs=[self.npc_selector, self.current_location, self.player_name_block, self.player_race_block, self.player_gender_block])
        chat_input.submit(self.game_interface.process_player_input, inputs=[chat_input, chat_box], outputs=[chat_input, chat_box, latest_voice_line])
        retry_button.click(self.game_interface.retry_last_input, inputs=[chat_box], outputs=[chat_input, chat_box, latest_voice_line])
        
    def get_conversation_type(self): # Returns the type of conversation as a string - none, single_npc_with_npc, single_player_with_npc, multi_npc
        return 'single_player_with_npc'
        
    # def message_handler(self, player_message):
    #     self.new_message({'role': self.config.user_name, 'name':"[player]", 'content': player_message}) # add player input to messages
    #     bot_message = random.choice(["How are you?", "I love you", "I'm very hungry"])
    #     return bot_message
        
    async def await_and_setup_conversation(self): # wait for player to select an NPC and setup the conversation when outside of conversation
        self.conversation_id = str(uuid.uuid4()) # Generate a unique ID for the conversation
        self.conversation_step += 1
        self.character_manager = characters_manager.Characters(self) # Reset character manager
        logging.info('\nConversations not starting when you select an NPC? Post an issue on the GitHub page: https://github.com/Pathos14489/Pantella')
        logging.info('\nWaiting for player to select an NPC...')
        try: # load character info, location and other gamestate data when data is available - Starts watching the _pantella_ files in the Skyrim folder and waits for the player to select an NPC
            character_info, self.current_location, self.player_name, self.player_race, self.player_gender = self.game_interface.load_game_state()
        except characters_manager.CharacterDoesNotExist as e:
            logging.info('Restarting...')
            logging.error(f"Error Loading Character<await_and_setup_conversation>: {e}")
        
        # setup the character that the player has selected
        character = self.setup_character(character_info)
        

        self.messages = [] # clear messages

        self.tokens_available = self.config.maximum_local_tokens - self.tokenizer.num_tokens_from_messages(self.get_context()) # calculate number of tokens available for the conversation

        self.game_interface.update_game_events() # update game events before first player input
        try: # get response from NPC to player greeting
            pp_name, _ = character.get_perspective_player_identity()
            self.new_message({'role': self.config.system_name, 'content': "*"+pp_name+" approaches "+character.name+" with the intent to start a conversation with them.*"}) # TODO: Improve later
        except Exception as e: # if error, close Pantella
            logging.error(f"Error Getting Response in await_and_setup_conversation(): {e}")
            tb = traceback.format_exc()
            logging.error(tb)
            input("Press Enter to exit.")
            raise e
        self.game_interface.update_game_events() # update game events before player input

        self.in_conversation = True
        self.conversation_ended = False
        
    async def step(self): # process player input and NPC response until conversation ends at each step of the conversation
        self.conversation_step += 1
        if self.in_conversation == False:
            logging.info('Cannot step through conversation when not in conversation')
            self.conversation_ended = True
            return

        self.update_game_state()
        logging.info('Stepping through conversation...')
        logging.info(f"Messages: {json.dumps(self.get_context(), indent=2)}")
        
        transcript_cleaned = ''
        transcribed_text = None
        if not self.conversation_ended: # check if conversation has ended, if it's not, get next player input
            logging.info('Getting player response...')
            
            transcribed_text = self.game_interface.get_player_response() # get player input
            self.behavior_manager.run_player_behaviors(transcribed_text) # run player behaviors
            transcript_cleaned = utils.clean_text(transcribed_text)
            self.new_message({'role': self.config.user_name, 'name':"[player]", 'content': transcribed_text}) # add player input to messages
            
            self.character_manager.before_step() # Let the characters know before a step has been taken
            self.update_game_state()

            active_character = self.character_manager.active_characters_list[0] # get the active character
            # check if user is ending conversation
            end_convo = False
            for keyword in active_character.language["end_conversation_keywords"]:
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
        
        if (transcribed_text is not None and transcribed_text != '') and not self.conversation_ended and self.in_conversation: # if player input is not empty and conversation has not ended, get response from NPC
            await self.get_response()
        
        logging.info(f"Response Generated")
        
        # if npc ended conversation
        if self.conversation_ended and self.in_conversation:
            self.end_conversation()

        self.character_manager.after_step() # Let the characters know after a step has been taken
        # if the conversation is becoming too long, save the conversation to memory and reload
        if self.tokenizer.num_tokens_from_messages(self.messages[1:]) > (round(self.tokens_available*self.config.conversation_limit_pct,0)): # if the conversation is becoming too long, save the conversation to memory and reload
            self.reload_conversation()