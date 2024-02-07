import logging
import src.behaviors.base_behavior as base_behavior

class strip(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Strip"
        self.description = "If {player} wants you to take off all your clothes, and you're comfortable and willing to do so, begin your response with 'Strip:'."
        self.example = "'Take off your clothes.' 'Strip: Okay, here goes.'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Strip behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} is stripping all their clothes off.")
                self.call_actor_method(speaker_character,"Wait","2")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"TakeEverythingOff")
        return "trade"
    