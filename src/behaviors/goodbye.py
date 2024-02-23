from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class goodbye(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Goodbye"
        self.description = "If {perspective_player_name} is leaving or ending the conversation, this behavior will be called."
        self.npc_post_keywords = ["goodbye", "bye", "farewell", "safe travels", "get away from me", "please leave me alone"]
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} is ending the conversation.")
                self.manager.conversation_manager.conversation_ended = True
        return "Goodbye"