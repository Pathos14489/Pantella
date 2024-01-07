import logging

class BaseBehavior():
    def __init__(self, manager):
        self.manager = manager
        self.keyword = "BASEBEHAVIOR"
    
    def run(self): # This should be overwritten by the child class
        logging.error("BaseBehavior run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return "BASEBEHAVIOR"