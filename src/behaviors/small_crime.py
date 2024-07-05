from src.logging import logging
import src.behaviors.base_behavior as base_behavior
import random

class small_crime(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "ReportSmallCrime"
        self.description = "If you want to report {perspective_player_name} for committing a minor crime, begin your response with 'ReportSmallCrime:'."
        # self.example = "'Haha! I stole your sweetroll!' 'ReportSmallCrime: I'm reporting you to the guards.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Public Menace",
                    "content":"Haha! I stole your sweetroll!"
                },
                {
                    "role": "assistant",
                    "content":"{command} I'm reporting you to the guards!"
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is trying to report the player for a minor crime.")
        self.new_game_event(f"{speaker_character.name} is reporting {self.manager.conversation_manager.player_name} for a minor crime to the guards.")
        self.queue_actor_method(speaker_character,"ModNonViolentCrime","100")