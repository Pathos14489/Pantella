import logging

class BaseBehavior():
    def __init__(self, manager):
        self.manager = manager
        self.keyword = None
        self.description = None
        self.example = None
        self.npc_pre_keywords = [] # Keywords that the NPC can say that will trigger this behavior before generating the voiceline
        self.npc_post_keywords = [] # Keywords that the NPC can say that will trigger this behavior after generating the voiceline

    @property
    def conversation_manager(self):
        return self.manager.conversation_manager
    
    def run(self, run=False, next_author=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                pass
        logging.error("BaseBehavior run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return "BASEBEHAVIOR"