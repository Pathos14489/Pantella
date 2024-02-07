import logging
import src.behaviors.base_behavior as base_behavior

class take(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Take"
        self.description = "If {player} wants to give you something, and you want to accept it, begin your response with 'Take:'."
        self.example = "'Can I give you this?' 'Take: Thank you, I appreciate it.'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Take behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to accept an item from the player.")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"OpenGiftMenu")
        return "trade"
    