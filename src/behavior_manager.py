import os
import logging

behaviors_dir = os.path.dirname(os.path.abspath(__file__)) + "/behaviors/"

class BehaviorManager():
    def __init__(self,conversation_manager):
        self.conversation_manager = conversation_manager
        self.behaviors = []
        for filename in os.listdir(behaviors_dir):
            if filename == "base_behavior.py":
                continue
            if filename.endswith(".py") and not filename.startswith("__"):
                logging.info("Loading behavior " + filename)
                behavior_name = filename.split(".py")[0]
                behavior = __import__("src.behaviors." + behavior_name, fromlist=[behavior_name])
                behavior = getattr(behavior, behavior_name)(self)
                print(behavior)
                if behavior.run(False) == "BASEBEHAVIOR":
                    logging.error("BaseBehavior run() called for " + behavior_name + ", this should be overwritten by the child class!")
                else:
                    logging.info("Loaded behavior " + filename)
                    self.behaviors.append(behavior)

    @property
    def behavior_keywords(self):
        return [behavior.keyword for behavior in self.behaviors]
    
    def evaluate(self, keyword, output_manager, characters, messages): # Returns True if the keyword was found and the behavior was run, False otherwise
        keyword = keyword.lower()
        for behavior in self.behaviors:
            if keyword == behavior.keyword.lower():
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run(True, output_manager, characters, messages)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def get_behavior_summary(self, player_name):
        summary = ""
        for behavior in self.behaviors:
            summary += f"{behavior.description} E.g. {behavior.example}\n".replace("{player}", player_name)
        return summary