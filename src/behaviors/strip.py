from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class strip(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Strip"
        self.description = "If [player] wants you to take off all your clothes, and you're comfortable and willing to do so, say '{command}' in your response."
        # self.example = "'Take off your clothes.' 'Strip: Okay, here goes.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Pervert",
                    "content":"Take off your clothes."
                },
                {
                    "role": "assistant",
                    "content":"{command} Okay, here goes..."
                },
            ],
            [
                {
                    "role": "user",
                    "name": "John Doe",
                    "content":"You should take a shower. Strip down and get in the tub."
                },
                {
                    "role": "assistant",
                    "content":"{command} Well, if you insist."
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is stripping all their clothes off.")
        self.new_game_event(f"{speaker_character.name} stripped all their clothes off and is now completely naked.")
        self.queue_actor_method(speaker_character,"Wait","2")
        self.queue_actor_method(speaker_character,"TakeEverythingOff")
