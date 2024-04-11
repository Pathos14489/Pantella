from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class stop_attacking(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "StopAttacking"
        self.description = "If {perspective_player_name} renounces their words, or you want to end combat, begin your response with 'StopAttacking:'."
        self.example = "'I'm sorry, I didn't mean it!' 'Forgiven: Alright, I'll forgive you.'"
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} stopped attacking.")
        self.new_game_event(f"{speaker_character.name} stopped attacking {self.manager.conversation_manager.player_name}, sheathed their weapon.")
        self.queue_actor_method(speaker_character,"StopCombat")