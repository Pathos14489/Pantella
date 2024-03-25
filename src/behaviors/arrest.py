from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class arrest(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Arrest"
        self.description = "If you want to arrest {perspective_player_name}, begin your response with 'Arrest:'."
        self.example = "'You're never take me alive!' 'Arrest: You're under arrest, criminal scum!'"
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Arrest behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} is trying to arrest the player.")
                self.new_game_event(f"{speaker_character.name} is trying to arrest {self.manager.conversation_manager.player_name}.")
                self.queue_actor_method(speaker_character,"ArrestPlayer")
        return "arrest"
    