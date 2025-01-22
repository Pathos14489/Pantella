from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class Behavior(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Trade"
        self.description = "If [player] wants full access to your inventory, and you want to let them have it, say '{command}' in your response."
        # self.example = "'Can we please trade items?' 'Trade: Of course my friend, what do you need?'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Dragonborn",
                    "content":"Can we please trade items?"
                },
                {
                    "role": "assistant",
                    "content":"{command} Of course my friend, what do you need?"
                },
            ]
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} wants to trade.")
        self.queue_actor_method(speaker_character,"Wait","2")
        self.new_game_event(f"{speaker_character.name} let {self.manager.conversation_manager.player_name} have full access to their bags and items.")
        self.queue_actor_method(speaker_character,"OpenTradeMenu")