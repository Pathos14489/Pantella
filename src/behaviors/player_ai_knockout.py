from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class player_ai_knockout(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Knockout"
        self.description = "If [player] wants to knock everyone in the conversation out, they can by speaking the magic words."
        self.valid_games = ["skyrim","skyrimvr"]
        self.player_only = True
    
    def player_run(self, sentence=None):
        formatted_sentence = sentence.lower().replace("'","").replace('"',"")
        if "deep and dreamless slumber" in formatted_sentence:
            logging.info(f"{self.manager.conversation_manager.player_name} is knocking everyone in the conversation out.")
            self.new_game_event(f"As {self.manager.conversation_manager.player_name} says those words, everyone else drops limp to the ground, like puppets with their strings cut.")
            for character in self.manager.conversation_manager.characters:
                self.queue_actor_method(character,"Knockout")
