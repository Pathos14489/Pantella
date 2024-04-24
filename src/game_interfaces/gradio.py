print("Importing game_interfaces/gradio.py")
from src.logging import logging, time
from src.game_interfaces.base_interface import BaseGameInterface
import src.utils as utils
logging.info("Imported required libraries in game_interfaces/gradio.py")

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
interface_slug = "gradio"

class GameInterface(BaseGameInterface):
    def __init__(self, conversation_manager, valid_games=valid_games, interface_slug=interface_slug):
        super().__init__(conversation_manager, valid_games, interface_slug)
        self.character_info = None
        self.current_location = None
        self.current_in_game_time = None
        self.player_name = None
        self.player_race = None
        self.player_gender = None
        self.player_input = None
        self.bot_response = None
        self.bot_response_audio = None
        
    def set_game_state(self, character_info, current_location, player_name, player_race, player_gender): # set the NPCs for the conversation
        logging.info(f"Setting conversation to be with NPCs: {character_info}")
        self.character_info = character_info
        self.active_character = self.conversation_manager.character_manager.add_character(character_info, False)
        self.current_location = current_location
        self.player_name = player_name
        self.player_race = player_race
        self.player_gender = player_gender
        
    def retry_last_input(self, history):
        """Retry the last input from the player"""
        self.conversation_manager.messages = self.conversation_manager.messages[:-1] # remove the last two messages from the conversation
        history = history[:-1] # remove the last two messages from the history
        player_input = history[-1][0] # set the player input to the last input
        self.player_input = player_input # set the player input
        self.bot_response = None # clear the bot response
        self.bot_response_audio = None # clear the bot response audio
        
        got_bot_response = False
        while not got_bot_response:
            try:
                if self.bot_response is not None:
                    got_bot_response = True
            except Exception as e:
                logging.error(f"Error getting bot response: {e}")
            time.sleep(0.1)
        bot_response = self.bot_response
        self.bot_response = None
        history.append((player_input, bot_response))
        return "", history, self.bot_response_audio

    def get_current_location(self, presume = ''):
        """Return the current location"""
        if self.current_location is None:
            return presume
        return self.current_location
        
    def is_conversation_ended(self):
        """Returns True if the conversation has ended, False otherwise."""
        return False
    
    def is_radiant_dialogue(self):
        """Returns True if the current dialogue is a radiant dialogue, False otherwise. - Radiant dialogues are dialogues that are initiated by the AI, not the player."""
        return False
    
    def get_current_context_string(self):
        """Returns the current context string set by the player. Or an empty string if no context is set."""
        return ""
    
    def queue_actor_method(self, actor_character, method_name, *args):
        """Queue an arbitrary method to be run on the actor in game via the game interface."""
        logging.info(f"Queuing actor method {method_name} with args {args} for actor {actor_character}")

    def end_conversation(self):
        """End the conversation in game."""
        return True
    
    def remove_from_conversation(self, character):
        """Remove the character from the conversation in game."""
        logging.info(f'Implement: Remove {character.name} from conversation in-game without ending the whole conversation')
    
    async def send_audio_to_external_software(self, queue_output):
        """Send audio file to external software e.g. Skyrim, Fallout 4, etc."""
        logging.info(f"Dialogue to play:", queue_output)
        self.bot_response_audio = queue_output[0]
        self.bot_response = queue_output[1]
    
    @utils.time_it
    def load_game_state(self):
        """ Tries to load the game state until it's ready """
        got_character_info = False
        while not got_character_info:
            try:
                if self.character_info is not None:
                    got_character_info = True
            except Exception as e:
                logging.error(f"Error getting character info: {e}")
            time.sleep(0.1)
        got_location = False
        while not got_location:
            try:
                if self.current_location is not None:
                    got_location = True
            except Exception as e:
                logging.error(f"Error getting location: {e}")
            time.sleep(0.1)
        got_player_name = False
        while not got_player_name:
            try:
                if self.player_name is not None:
                    got_player_name = True
            except Exception as e:
                logging.error(f"Error getting player name: {e}")
            time.sleep(0.1)
        got_player_race = False
        while not got_player_race:
            try:
                if self.player_race is not None:
                    got_player_race = True
            except Exception as e:
                logging.error(f"Error getting player name: {e}")
            time.sleep(0.1)
        got_player_gender = False
        while not got_player_gender:
            try:
                if self.player_gender is not None:
                    got_player_gender = True
            except Exception as e:
                logging.error(f"Error getting player name: {e}")
            time.sleep(0.1)
        return self.character_info, self.current_location, self.player_name, self.player_race, self.player_gender
            
    def process_player_input(self, player_input, history=[]):
        """Set the player input"""
        logging.info(f"Setting player input: {player_input}")
        self.player_input = player_input
        got_bot_response = False
        while not got_bot_response:
            try:
                if self.bot_response is not None:
                    got_bot_response = True
            except Exception as e:
                logging.error(f"Error getting bot response: {e}")
            time.sleep(0.1)
        bot_response = self.bot_response
        self.bot_response = None
        history.append((player_input, bot_response))
        return "", history, self.bot_response_audio
        
    def get_player_input(self):
        got_player_input = False
        while not got_player_input:
            try:
                if self.player_input is not None:
                    got_player_input = True
            except Exception as e:
                logging.error(f"Error getting player input: {e}")
            time.sleep(0.1)
        player_input = self.player_input
        self.player_input = None
        return player_input