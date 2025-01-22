from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class Behavior(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Wakeup"
        self.description = "If [player] wants to wake everyone in the conversation up, they can by speaking the magic words."
        self.valid_games = ["skyrim","skyrimvr"]
        self.player_only = True
    
    def player_run(self, sentence=None):
        formatted_sentence = sentence.lower().replace("'","").replace('"',"")
        if "bring yourself back online" in formatted_sentence or "bring yourselves back online" in formatted_sentence or "bring yourself online" in formatted_sentence or "bring yourselves online" in formatted_sentence:
            logging.info(f"{self.manager.conversation_manager.player_name} is waking everyone in the conversation up.")
            self.new_game_event(f"As {self.manager.conversation_manager.player_name} says those words, everyone else starts to move again and picks themselves up off the ground.")
            for character in self.manager.conversation_manager.characters:
                self.queue_actor_method(character,"WakeUp")