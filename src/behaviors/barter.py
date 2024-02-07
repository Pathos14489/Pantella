import logging
import src.behaviors.base_behavior as base_behavior

class barter(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Barter"
        self.description = "If {player} wants to barter with you, and you want to barter with them, begin your response with 'Barter:'."
        self.example = "'Hey, can I sell you something/buy something from you?' 'Barter: Sure, what do you have?'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Barter behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to barter.")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"OpenBarterMenu")
        return "trade"
    