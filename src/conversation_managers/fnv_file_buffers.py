print("Loading conversation_managers/fnv_file_buffers.py...")
from src.logging import logging
from src.conversation_managers.creation_engine_file_buffers import ConversationManager as CreationEngineFileBuffersConversationManager
logging.info("Imported required libraries in conversation_managers/fnv_file_buffers.py")

valid_games = ["falloutnv"]
manager_slug = "fnv_file_buffers"

class ConversationManager(CreationEngineFileBuffersConversationManager):
    def __init__(self, config, initialize=True):
        super().__init__(config, initialize)
        print("Loading Fallout: New Vegas File Buffers Conversation Manager")
        self.current_in_game_time = None
        if initialize and self.config.ready:
            self.current_in_game_time = self.game_interface.get_dummy_game_time() # Initialised at start of every conversation in await_and_setup_conversation()
        self.radiant_dialogue = False # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_gender = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.player_race = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.current_location = 'Mojave Wasteland' # Initialised at start of every conversation in await_and_setup_conversation()
        logging.info(f"Creation Engine (File Buffer) Conversation Manager Initialized")
        if initialize:
            self.game_interface.display_status('Started Pantella')
            
    def get_conversation_type(self): # Returns the type of conversation as a string - none, single_npc_with_npc, single_player_with_npc, multi_npc
        return 'single_player_with_npc'
    
    def get_current_context_string(self):
        """Wait for context string to populate"""
        return ""