import logging
import src.behaviors.base_behavior as base_behavior

class trade(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Give"
        self.description = "If {player} wants full access to your inventory, and you want to let them have it, begin your response with 'Trade:'."
        self.example = "'Can we please trade items?' 'Trade: Of course my friend, what do you need?'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Trade behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to trade.")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"OpenTradeMenu")
        return "trade"
    