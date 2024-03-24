from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class take(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Take"
        self.description = "If {perspective_player_name} wants to give you something, or pay you directly, and you want to accept it, begin your response with 'Take:'."
        self.example = "'Can I give you this?' 'Take: Thank you, I appreciate it.'" "'Here's a thousand septims.' 'Take: Thank you, I appreciate it.'"
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Take behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to accept an item from the player.")
                self.queue_actor_method(speaker_character,"Wait","2")
                self.new_game_event(f"{speaker_character.name} offered to take something from {self.manager.conversation_manager.player_name}.")
                self.queue_actor_method(speaker_character,"OpenGiftMenu")
        return "take"
    