import logging
import src.behaviors.base_behavior as base_behavior

class offended(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Offended"
        self.description = "If {perspective_player_name} says something hurtful / offensive, begin your response with 'Offended:'."
        self.example = "'Have you washed lately?' 'Offended: How dare you!'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Offended behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} got offended.")
                self.new_game_event(f"{speaker_character.name} got so offended by {self.manager.conversation_manager.player_name}'s comment, they drew their weapon and started combat.")
                self.queue_actor_method(speaker_character,"StartCombat")
        return "offended"
    