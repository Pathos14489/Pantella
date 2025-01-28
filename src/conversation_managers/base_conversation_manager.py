print("base_conversation_manager.py executed")
from src.logging import logging, time
import asyncio
import src.game_interface as game_interface
import src.characters_manager as characters_manager # Character Manager class
import src.behavior_manager as behavior_manager
import src.language_model as language_models
import src.thought_process as thought_process
import src.character_generator as character_generator
import src.tts as tts
# import src.stt as stt
import src.character_db as character_db
import uuid
import json
logging.info("Imported required libraries in base_conversation_manager.py")

valid_games = []
manager_slug = "base_conversation_manager"

class BaseConversationManager:
    def __init__(self, config, initialize=True):
        self.config = config
        self.config.conversation_manager = self
        if initialize and self.config.ready:
            self.pre_initialization()
        if self.config.ready:
            self.synthesizer = tts.create_Synthesizer(self, self.config.tts_engine) # Create Synthesizer object based on config - required by scripts for checking voice models, so is left out of self.pre_initialization() and self.post_initialization() intentionally
            self.character_database = character_db.CharacterDB(self) # Create Character Database Manager based on config - required by scripts for merging, patching and converting character databases, so is left out of self.pre_initialization() and self.post_initialization() intentionally
            self.character_manager = characters_manager.Characters(self) # Reset character manager
        if self.config.linux_mode:
            with open("./version", "r") as f:
                self.pantella_version = f.read().strip() # Read Pantella version from file
        else:            
            with open(".\\version", "r") as f:
                self.pantella_version = f.read().strip() # Read Pantella version from file
        if initialize and self.config.ready:
            self.post_initialization()
            logging.info(f'Pantella v{self.pantella_version} Initialized')
        self.in_conversation = False # Whether or not the player is in a conversation
        self.conversation_ended = False # Whether or not the conversation has ended
        self.player_name = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.tokens_available = 0 # Initialised at start of every conversation in await_and_setup_conversation()
        self.messages = [] # Initialised at start of every conversation in await_and_setup_conversation()
        self.conversation_step = 0 # The current step of the conversation - 0 is before any conversation has started, 1 is the first step of the conversation, etc.
        self.restart = False # Can be set at any time to force restart of conversation manager - Will ungracefully end any ongoing conversation client side
        self.conversation_id = str(uuid.uuid4()) # Generate a unique ID for the conversation
        if initialize:
            self.current_in_game_time = self.game_interface.get_dummy_game_time() # Initialised at start of every conversation in await_and_setup_conversation()

    def setup_character(self, character_info):
        character = self.character_manager.add_character(character_info) # setup the character that the player has selected
        # self.synthesizer.change_voice(character)
        self.game_interface.active_character = character
        self.game_interface.character_num = 0
        return character
    
    def update_game_state(self):
        self.conversation_ended = self.game_interface.is_conversation_ended() # wait for the game to indicate that the conversation has ended or not
        self.game_interface.update_game_events() # update game events before player input
        self.current_in_game_time = self.game_interface.get_current_game_time() # update current in game time each step of the conversation
    
    def new_message(self, msg):
        """Add a new message to the conversation"""
        msg["id"] = str(uuid.uuid4()) # Generate a unique ID for the message
        msg["timestamp"] = time.time() # Add timestamp to message
        msg["location"] = self.game_interface.get_current_location() # Add location to message
        if "type" not in msg:
            msg["type"] = "message" # Add type to message
        self.messages.append(msg)
        self.character_manager.add_message(msg)

    def has_message(self, message):
        """Check if the conversation has a message"""
        has_message = False
        for msg in self.messages:
            if msg["id"] == message["id"]:
                has_message = True
                break
            if msg["role"] == message["role"] and msg["content"] == message["content"]:
                has_message = True
                break
        return has_message

    def get_conversation_type(self): # Returns the type of conversation as a string - none, single_npc_with_npc, single_player_with_npc, multi_npc
        if self.character_manager is None:
            return 'none'
        if len(self.character_manager.active_characters) == 0:
            return 'none'
        elif len(self.character_manager.active_characters) == 1 and not self.radiant_dialogue:
            return 'single_player_with_npc'
        elif len(self.character_manager.active_characters) == 1 and self.radiant_dialogue:
            return 'single_npc_with_npc'
        else:
            return 'multi_npc'

    def pre_initialization(self):
        self.llm, self.tokenizer = language_models.create_LLM(self) # Create LLM and Tokenizer based on config

    def post_initialization(self):
        self.thought_process = thought_process.create_thought_process(self) # Create Thought Process Manager based on config
        self.character_generator_schema = character_generator.create_generator_schema(self) # Create Character Manager based on config
        self.config.set_prompt_style(self.llm) # Set prompt based on LLM and config settings
        self.game_interface = game_interface.create_game_interface(self) # Create Game Interface based on config
        self.behavior_manager = behavior_manager.create_manager(self) # Create Behavior Manager based on config
        
    def get_context(self): # Returns the current context(in the form of a list of messages) for the given active characters in the ongoing conversation
        return self.llm.get_context()
    
    def get_loggable_context(self): # Returns the current context(in the form of a list of messages) for the given active characters in the ongoing conversation
        messages = self.get_context()
        loggable_context = []
        for message in messages:
            if type(message["content"]) == str:
                loggable_context.append(message)
            else:
                new_content = []
                for content in message["content"]:
                    if content["type"] == "image_url":
                        new_content.append({
                            "type": "image_url",
                            "url":"<image_url>"
                        })
                    else:
                        new_content.append(content)
                loggable_context.append({
                    "role": message["role"],
                    "content": new_content
                })
                logging.info(f"Loggable context: {json.dumps(loggable_context, indent=4)}")
                # input("Press enter to continue")
        return loggable_context
    
    async def get_response(self, force_speaker=None):
        """Get response from LLM and NPC(s) in the conversation"""
        sentence_queue = asyncio.Queue() # Create queue to hold sentences to be processed
        event = asyncio.Event() # Create event to signal when the response has been received
        event.set() # Set event to true to allow the first sentence to be processed

        await asyncio.gather(
            self.llm.process_response(sentence_queue, event, force_speaker=force_speaker),
            self.game_interface.send_response(sentence_queue, event)
        )

    async def await_and_setup_conversation(self):
        """Wait for the conversation to begin and setup the conversation"""
        logging.error("await_and_setup_conversation() not implemented in BaseConversationManager")
        raise NotImplementedError
    
    async def step(self):
        """Step through the conversation"""
        logging.error("step() not implemented in BaseConversationManager")
        raise NotImplementedError
    
    def reload_conversation(self):
        """Reload the conversation - Used when the conversation has ended or the conversation limit has been reached"""
        self.character_manager.reached_conversation_limit()
        self.messages = self.messages[-self.config.reload_buffer:] # save the last few messages to reload the conversation