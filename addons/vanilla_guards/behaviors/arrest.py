from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class Behavior(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Arrest"
        self.description = "If you want to arrest [player] for committing a crime, say '{command}' in your response."
        self.guard_only = True
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Bandit",
                    "content":"*Running away with stolen goods.* I'm outta here!"
                },
                {
                    "role": "assistant",
                    "content":"{command} Stop right there, criminal scum! Nobody breaks the law on my watch!"
                },
            ],
            [
                {
                    "role": "user",
                    "name": "Bandit",
                    "content":"*Stabbing a lady in the middle of Whiterun Marketplace.* Die, wench!"
                },
                {
                    "role": "assistant",
                    "content":"{command} You there, stop! *The guard draws their sword and runs towards the bandit.*"
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is trying to arrest the player for a crime.")
        self.new_game_event(f"{speaker_character.name} is attempting to arrest [player] for a crime.")
        self.queue_actor_method(speaker_character,"ModViolentCrime","1000")