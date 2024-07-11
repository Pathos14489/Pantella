from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class player_ai_override_on(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "EnableAI"
        self.description = "If [player] wants to let everyone in the conversation move again, they can by speaking the magic words."
        self.valid_games = ["skyrim","skyrimvr"]
        self.player_only = True
    
    def player_run(self, sentence=None):
        formatted_sentence = sentence.lower().replace("'","").replace('"',"")
        if "as you were" == formatted_sentence:
            logging.info(f"{self.manager.conversation_manager.player_name} is letting everyone in the conversation move again.")
            self.new_game_event(f"As {self.manager.conversation_manager.player_name} says those words, everyone else starts to move again.")
            for character in self.manager.conversation_manager.characters:
                self.queue_actor_method(character,"EnableAI")