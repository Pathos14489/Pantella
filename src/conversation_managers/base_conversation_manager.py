import asyncio
from src.logging import logging
import pandas as pd
import src.game_interface as game_interface
import src.chat_manager as chat_manager
import src.characters_manager as characters_manager # Character Manager class
import src.behavior_manager as behavior_manager
import src.language_model as language_models
import src.tts as tts
import src.stt as stt
import src.character_db as character_db

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

    def create_new_character_manager(self):
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
        
    def get_context(self, chat_completions=False): # Returns the current context(in the form of a list of messages) for the given active characters in the ongoing conversation
        system_prompt = self.character_manager.get_system_prompt()
        msgs = [{'role': self.config.system_name, 'content': system_prompt}]
        msgs.extend(self.messages) # add messages to context
        
        formatted_messages = [] # format messages to be sent to LLM - Replace [player] with player name appropriate for the type of conversation
        for msg in msgs: # Add player name to messages based on the type of conversation
            if chat_completions: # Format for chat completions
                if msg['role'] == "[player]":
                    if self.character_manager.active_character_count() > 1: # if multi NPC conversation use the player's actual name
                        formatted_messages.append({
                            'role': self.config.user_name,
                            'name': self.player_name,
                            'content': msg['content']
                        })
                    else: # if single NPC conversation use the NPC's perspective player name
                        perspective_player_name, perspective_player_description, trust = self.chat_manager.active_character.get_perspective_player_identity()
                        formatted_messages.append({
                            'role': self.config.user_name,
                            'name': perspective_player_name,
                            'content': msg['content']
                        })
                else:
                    if msg['role'] == self.config.system_name:
                        formatted_messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })
                    else:
                        formatted_messages.append({
                            'role': self.config.assistant_name,
                            'name': msg['role'],
                            'content': msg['content']
                        })
            else: # Format for Normal LLM Prompting
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

    def await_and_setup_conversation(self):
        """Wait for the conversation to begin and setup the conversation"""
        logging.error("await_and_setup_conversation() not implemented in BaseConversationManager")
        raise NotImplementedError
    
    def step(self):
        """Step through the conversation"""
        logging.error("step() not implemented in BaseConversationManager")
        raise NotImplementedError