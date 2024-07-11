from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class take(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Take"
        self.description = "If [player] wants to give you something, or pay you directly, and you want to accept it, say '{command}' in your response."
        # self.example = "'Can I give you this?' 'Take: Thank you, I appreciate it.'" "'Here's a thousand septims.' 'Take: Thank you, I appreciate it.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "The Gifter",
                    "content":"Can I give you this?"
                },
                {
                    "role": "assistant",
                    "content":"{command} Thank you, I appreciate it."
                },
            ],
            [
                {
                    "role": "user",
                    "name": "John Doe",
                    "content":"Here's a thousand septims."
                },
                {
                    "role": "assistant",
                    "content":"{command} Oh wow! Thank you so much!"
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} wants to accept an item from the player.")
        self.queue_actor_method(speaker_character,"Wait","2")
        self.new_game_event(f"{speaker_character.name} offered to take something from {self.manager.conversation_manager.player_name}.")
        self.queue_actor_method(speaker_character,"OpenGiftMenu")
