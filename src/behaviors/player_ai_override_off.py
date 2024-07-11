from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class player_ai_override_off(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "DisableAI"
        self.description = "If [player] wants to stop everyone in the conversation from moving, they can by speaking the magic words."
        self.valid_games = ["skyrim","skyrimvr"]
        self.player_only = True
    
    def player_run(self, sentence=None):
        formatted_sentence = sentence.lower().replace("'","").replace('"',"")
        if "cease all motor functions" in formatted_sentence or "freeze all motor functions" in formatted_sentence or "stop all motor functions" in formatted_sentence:
            logging.info(f"{self.manager.conversation_manager.player_name} is stopping everyone in the conversation from moving.")
            self.new_game_event(f"As {self.manager.conversation_manager.player_name} says those words, everyone else stops moving.")
            for character in self.manager.conversation_manager.characters:
                self.queue_actor_method(character,"DisableAI")