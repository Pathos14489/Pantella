print("base_conversation_manager.py executed")
from src.logging import logging, time
import asyncio
import pandas as pd
import src.game_interface as game_interface
import src.chat_manager as chat_manager
import src.characters_manager as characters_manager # Character Manager class
import src.behavior_manager as behavior_manager
import src.language_model as language_models
import src.tts as tts
import src.stt as stt
import src.character_db as character_db
import uuid
logging.info("Imported required libraries in base_conversation_manager.py")

valid_games = []
manager_slug = "base_conversation_manager"

class BaseConversationManager:
    def __init__(self, config, initialize=True):
        self.config = config
        self.config.conversation_manager = self
        self.language_info = self.get_language_info()
        if self.config.ready:
            self.synthesizer = tts.create_Synthesizer(self) # Create Synthesizer object based on config - required by scripts for checking voice models, so is left out of self.initialize() intentionally
            self.character_database = character_db.CharacterDB(self) # Create Character Database Manager based on config - required by scripts for merging, patching and converting character databases, so is left out of self.initialize() intentionally
        with open("./version", "r") as f:
            self.mantella_version = f.read().strip() # Read Pantella version from file
        if initialize and self.config.ready:
            self.initialize()
            logging.info(f'Pantella v{self.mantella_version} Initialized')
        self.in_conversation = False # Whether or not the player is in a conversation
        self.conversation_ended = False # Whether or not the conversation has ended
        self.player_name = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.tokens_available = 0 # Initialised at start of every conversation in await_and_setup_conversation()
        self.messages = [] # Initialised at start of every conversation in await_and_setup_conversation()
        self.conversation_step = 0 # The current step of the conversation - 0 is before any conversation has started, 1 is the first step of the conversation, etc.
        self.restart = False # Can be set at any time to force restart of conversation manager - Will ungracefully end any ongoing conversation client side
        self.conversation_id = str(uuid.uuid4()) # Generate a unique ID for the conversation

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

    def create_new_character_manager(self):
        """Create a new Character Manager object based on the current ConversationManager object"""
        return characters_manager.Characters(self) # Create Character Manager object based on ConversationManager
            
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
        self.game_interface = game_interface.create_game_interface(self) # Create Game Interface based on config
        self.chat_manager = chat_manager.create_manager(self) # Create Chat Manager based on config
        self.transcriber = stt.Transcriber(self)
        self.behavior_manager = behavior_manager.create_manager(self) # Create Behavior Manager based on config
        
    def get_context(self): # Returns the current context(in the form of a list of messages) for the given active characters in the ongoing conversation
        return self.llm.get_context()
    
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

    def await_and_setup_conversation(self):
        """Wait for the conversation to begin and setup the conversation"""
        logging.error("await_and_setup_conversation() not implemented in BaseConversationManager")
        raise NotImplementedError
    
    def step(self):
        """Step through the conversation"""
        logging.error("step() not implemented in BaseConversationManager")
        raise NotImplementedError
    
    def reload_conversation(self):
        """Reload the conversation - Used when the conversation has ended or the conversation limit has been reached"""
        self.character_manager.reached_conversation_limit()
        self.messages = self.messages[-self.config.reload_buffer:] # save the last few messages to reload the conversation