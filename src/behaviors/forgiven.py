from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class forgiven(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Forgiven"
        self.description = "If {perspective_player_name} renounces their words, or to end combat, begin your response with 'Forgiven:'."
        self.example = "'I'm sorry, I didn't mean it!' 'Forgiven: Alright, I'll forgive you.'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Forgiven behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} forgave someone.")
                self.new_game_event(f"{speaker_character.name} forgave {self.manager.conversation_manager.player_name}, and ended combat, sheathing their weapon.")
                self.queue_actor_method(speaker_character,"StopCombat")
        return "forgiven"