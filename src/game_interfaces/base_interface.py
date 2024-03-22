from src.logging import logging

valid_games = []
interface_slug = "base_game_interface"

class BaseGameInterface:
    def __init__(self, conversation_manager, valid_games=valid_games, interface_slug=interface_slug):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.game_id = self.config.game_id
        self.valid_games = valid_games
        self.interface_slug = interface_slug
        if self.interface_slug == "base_game_interface":
            logging.error(f"Interface slug not implemented for interface {self.__class__.__name__}")
            raise NotImplementedError
        if self.game_id not in self.valid_games:
            logging.error(f"Game '{self.game_id}' not supported by interface {self.interface_slug}")
            return
        logging.info(f"Loading Game Interface...")
        
    def is_conversation_ended(self):
        """Returns True if the conversation has ended, False otherwise."""
        raise NotImplementedError
    
    def is_radiant_dialogue(self):
        """Returns True if the current dialogue is a radiant dialogue, False otherwise. - Radiant dialogues are dialogues that are initiated by the AI, not the player."""
        return False
    
    def get_current_context_string(self):
        """Returns the current context string set by the player. Or an empty string if no context is set."""
        return ""
    
    def queue_actor_method(self, actor_character, method_name, *args):
        """Queue an arbitrary method to be run on the actor in game via the game interface."""
        raise NotImplementedError