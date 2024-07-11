from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class stop_attacking(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "StopAttacking"
        self.description = "If [player] renounces their words, or you want to end combat, say '{command}' in your response."
        # self.example = "'I'm sorry, I didn't mean it!' 'StopAttacking: Alright, I'll forgive you.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Beaver Cleaver",
                    "content":"I'm sorry, I didn't mean it!"
                },
                {
                    "role": "assistant",
                    "content":"{command} Alright, I'll forgive you."
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} stopped attacking.")
        self.new_game_event(f"{speaker_character.name} stopped attacking {self.manager.conversation_manager.player_name}, sheathed their weapon.")
        self.queue_actor_method(speaker_character,"StopCombat")