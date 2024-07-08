from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class big_crime(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "ReportBigCrime"
        self.description = "If you want to report {perspective_player_name} for committing a really bad crime, say '{command}' in your response."
        # self.example = "'Haha! I killed your family!' 'ReportBigCrime: Guards! Guards help!' 'I'm going to murder you!' 'ReportBigCrime: Guards, help me! Someone call the guards!'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Bandit",
                    "content":"Haha! I killed your family!"
                },
                {
                    "role": "assistant",
                    "content":"{command} Guards! Guards help!"
                },
            ],
            [
                {
                    "role": "user",
                    "name": "Bandit",
                    "content":"I'm going to murder you!"
                },
                {
                    "role": "assistant",
                    "content":"{command} Guards, help me! Someone call the guards!"
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is trying to report the player for a crime.")
        self.new_game_event(f"{speaker_character.name} is reporting {self.manager.conversation_manager.player_name} for a crime to the guards.")
        self.queue_actor_method(speaker_character,"ModViolentCrime","1000")