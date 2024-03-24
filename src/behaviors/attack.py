from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class attack(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Attack"
        self.description = "If you want to attack {perspective_player_name}, begin your response with 'Attack:'."
        self.example = "'Give me your money or I'll kill you!' 'Attack: Never, criminal scum!'"
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Attack behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} attacked the player.")
                self.new_game_event(f"{speaker_character.name} drew their weapon and started attacking {self.manager.conversation_manager.player_name}.")
                self.queue_actor_method(speaker_character,"StartCombat")
        return "attack"
    