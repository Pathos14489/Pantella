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
    
    def evaluate(self, keyword, sentence): # Returns True if the keyword was found and the behavior was run, False otherwise
        logging.info(f"Evaluating keyword {keyword} in sentence {sentence}")
        for behavior in self.behaviors:
            if behavior.keyword is not None and behavior.keyword.lower() == keyword.lower():
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run(True, sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def pre_sentence_evaluate(self,sentence): # Evaluates just the sentence, returns the behavior that was run
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_pre_keywords
            npc_words = sentence.replace(",", "").replace(".", "").replace("!", "").replace("?", "").lower()
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if npc_keyword.lower() in npc_words:
                    npc_contains_keyword = True
            if npc_contains_keyword:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run(True, sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def post_sentence_evaluate(self,sentence): # Evaluates just the sentence, returns the behavior that was run
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_post_keywords
            npc_words = sentence.replace(",", "").replace(".", "").replace("!", "").replace("?", "").lower()
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if npc_keyword.lower() in npc_words:
                    npc_contains_keyword = True
            if npc_contains_keyword:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run(True, sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def get_behavior_summary(self):
        summary = ""
        for behavior in self.behaviors:
            if behavior.description is not None:
                summary += f"{behavior.description}"
                if behavior.example is not None:
                    summary += f"  E.g. {behavior.example}"
                summary += "\n"
        summary = summary.replace("{player}", self.conversation_manager.player_name)
        return summary