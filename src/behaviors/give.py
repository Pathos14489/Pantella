import logging
import src.behaviors.base_behavior as base_behavior

class give(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Give"
        self.description = "If {player} wants to take something from you, and you want to give it to them, begin your response with 'Give:'."
        self.example = "'Can you give me that?' 'Give: Sure, here you go.'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Give behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to give an item from the player.")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"OpenTakeMenu")
        return "trade"
    