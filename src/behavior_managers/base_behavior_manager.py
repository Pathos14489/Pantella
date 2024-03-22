import os
from src.logging import logging

behaviors_dir =  os.path.join(os.path.dirname(os.path.abspath(__file__)),"../behaviors/")

valid_games = []
manager_slug = "base_behavior_manager"

class base_BehaviorManager():
    def __init__(self,conversation_manager):
        self.conversation_manager = conversation_manager
        self.behaviors = []
        self.named_behaviors = {}
        for filename in os.listdir(behaviors_dir):
            if filename == "base_behavior.py":
                continue
            if filename.endswith(".py") and not filename.startswith("__"):
                logging.info("Loading behavior " + filename)
                behavior_name = filename.split(".py")[0]
                behavior = __import__("src.behaviors." + behavior_name, fromlist=[behavior_name])
                behavior = getattr(behavior, behavior_name)(self)
                # logging.info(behavior)
                if conversation_manager.config.game_id in behavior.valid_games:
                    logging.info(f"Behavior {behavior_name} supported by game '{conversation_manager.config.game_id}'")
                else:
                    logging.info(f"Behavior {behavior_name} not supported by game '{conversation_manager.config.game_id}'")
                    continue
                if behavior.run(False) == "BASEBEHAVIOR":
                    logging.error("BaseBehavior run() called for " + behavior_name + ", this should be overwritten by the child class!")
                else:
                    logging.info("Loaded behavior " + filename)
                    self.behaviors.append(behavior)
                    self.named_behaviors[behavior_name] = behavior

    @property
    def behavior_keywords(self):
        return [behavior.keyword for behavior in self.behaviors]
    
    def evaluate(self, keyword, next_author, sentence): # Returns True if the keyword was found and the behavior was run, False otherwise
        logging.info(f"Evaluating keyword {keyword} in sentence {sentence}")
        for behavior in self.behaviors:
            if behavior.valid():
                if behavior.keyword is not None and behavior.keyword.lower() == keyword.lower():
                    logging.info(f"Behavior triggered: {behavior.keyword}")
                    try:
                        behavior.run(True, next_author, sentence)
                        return behavior
                    except Exception as e:
                        logging.error(f"Error running behavior {behavior.keyword}: {e}")
                        raise e
        return None
    
    def pre_sentence_evaluate(self, next_author, sentence): # Evaluates just the sentence, returns the behavior that was run
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_pre_keywords
            npc_words = sentence.replace(",", "").replace(".", "").replace("!", "").replace("?", "").lower()
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if npc_keyword.lower() in npc_words:
                    npc_contains_keyword = True
            for activation_sentence in behavior.activation_sentences:
                if activation_sentence.lower() in sentence.lower() or sentence.lower() in activation_sentence.lower():
                    npc_contains_keyword = True
            if npc_contains_keyword:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior.run(True, sentence=sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def post_sentence_evaluate(self,next_author, sentence): # Evaluates just the sentence, returns the behavior that was run
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_post_keywords
            npc_words = sentence.replace(",", "").replace(".", "").replace("!", "").replace("?", "").lower()
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if npc_keyword.lower() in npc_words:
                    npc_contains_keyword = True
            for activation_sentence in behavior.activation_sentences:
                if activation_sentence.lower() in sentence.lower() or sentence.lower() in activation_sentence.lower():
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
            if behavior.valid():
                if behavior.description is not None:
                    summary += f"{behavior.description}\n"
                    if behavior.example is not None:
                        summary += f"Example: {behavior.example}"
                    summary += "\n"
        return summary