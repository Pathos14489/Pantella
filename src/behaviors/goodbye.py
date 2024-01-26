import logging
import src.behaviors.base_behavior as base_behavior

class goodbye(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.npc_post_keywords = ["goodbye", "bye", "farewell", "safe travels", "get away from me", "please leave me alone"]
    
    def run(self, run=False, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                logging.info(f"The NPC is saying goodbye.")
                self.manager.conversation_manager.conversation_ended = True
        return "Goodbye"