import os
import logging

behaviors_dir = os.path.dirname(os.path.abspath(__file__)) + "/behaviors/"

class BehaviorManager():
    def __init__(self,conversation_manager):
        self.conversation_manager = conversation_manager
        self.behaviors = []
        for filename in os.listdir(behaviors_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                behavior_name = filename.split(".py")[0]
                behavior = __import__("src.behaviors." + behavior_name, fromlist=[behavior_name])
                behavior = getattr(behavior, behavior_name)
                if behavior.run() == "BASEBEHAVIOR":
                    logging.error("BaseBehavior run() called for " + behavior_name + ", this should be overwritten by the child class!")
                else:
                    self.behaviors.append(behavior(self))

    @property
    def behavior_keywords(self):
        return [behavior.keyword for behavior in self.behaviors]
    
    def evaluate(self, keyword): # Returns True if the keyword was found and the behavior was run, False otherwise
        keyword = keyword.lower()
        for behavior in self.behaviors:
            if keyword == behavior.keyword.lower():
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run()
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
                return True
        return False