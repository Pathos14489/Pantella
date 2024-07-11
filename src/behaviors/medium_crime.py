from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class medium_crime(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "ReportCrime"
        self.description = "If you want to report [player] for committing a crime, say '{command}' in your response."
        # self.example = "'Haha! I stole all the Jarl's gold!' 'ReportCrime: That's a crime! I'm reporting you to the guards.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Thief",
                    "content":"Haha! I stole all the Jarl's gold!"
                },
                {
                    "role": "assistant",
                    "content":"{command} That's a crime! I'm reporting you to the guards."
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is trying to report the player for a crime.")
        self.new_game_event(f"{speaker_character.name} is reporting {self.manager.conversation_manager.player_name} for a crime to the guards.")
        self.queue_actor_method(speaker_character,"ModNonViolentCrime","500")