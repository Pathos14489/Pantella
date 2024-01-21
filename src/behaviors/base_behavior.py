import logging

class BaseBehavior():
    def __init__(self, manager):
        self.manager = manager
        self.keyword = "BASEBEHAVIOR"
        self.description = "BASEBEHAVIOR"
        self.example = "BASEBEHAVIOR"
        self.npc_keywords = []
    
    def run(self, run=False, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                pass
        logging.error("BaseBehavior run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return "BASEBEHAVIOR"