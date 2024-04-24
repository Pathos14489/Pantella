print("Importing base_behavior_manager.py...")
from src.logging import logging
import os
logging.info("Imported required libraries in base_behavior_manager.py")

behaviors_dir =  os.path.join(os.path.dirname(os.path.abspath(__file__)),"../behaviors/")

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
manager_slug = "default_behavior_manager"

class BehaviorManager():
    def __init__(self,conversation_manager):
        self.conversation_manager = conversation_manager
        self.behaviors = []
        self.named_behaviors = {}
        logging.info("Loading behaviors...")
        for filename in os.listdir(behaviors_dir):
            if filename == "base_behavior.py":
                continue
            if filename.endswith(".py") and not filename.startswith("__"):
                # logging.info("Loading behavior " + filename)
                behavior_name = filename.split(".py")[0]
                behavior = __import__("src.behaviors." + behavior_name, fromlist=[behavior_name])
                behavior = getattr(behavior, behavior_name)(self)
                # logging.info(behavior)
                if conversation_manager.config.game_id in behavior.valid_games:
                    logging.info(f"Behavior {behavior_name} supported by game '{conversation_manager.config.game_id}'")
                else:
                    logging.info(f"Behavior {behavior_name} not supported by game '{conversation_manager.config.game_id}'")
                    continue
                if behavior._run(False) == "BASEBEHAVIOR":
                    logging.error("BaseBehavior run() called for " + behavior_name + ", this should be overwritten by the child class!")
                else:
                    # logging.info("Loaded behavior " + filename)
                    self.behaviors.append(behavior)
                    self.named_behaviors[behavior_name] = behavior
        logging.info("Loaded default behavior manager")

    @property
    def behavior_keywords(self):
        """Return a list of all behavior keywords."""
        return [behavior.keyword for behavior in self.behaviors]
    
    def evaluate(self, keyword, next_author, sentence): # Returns True if the keyword was found and the behavior was run, False otherwise
        """Evaluate the keyword for behaviors that should run."""
        logging.info(f"Evaluating keyword {keyword} in sentence {sentence}")
        for behavior in self.behaviors:
            if behavior.valid():
                if behavior.keyword is not None and behavior.keyword.lower() == keyword.lower():
                    logging.info(f"Behavior triggered: {behavior.keyword}")
                    try:
                        if behavior.player_only:
                            logging.error(f"Behavior {behavior.keyword} is player-only!")
                            return False
                        behavior._run(True, next_author, sentence=sentence)
                        return behavior
                    except Exception as e:
                        logging.error(f"Error running behavior {behavior.keyword}: {e}")
                        raise e
        return None
    
    def pre_sentence_evaluate(self, next_author, sentence): # Evaluates just the sentence, returns the behavior that was run
        """Evaluate the sentence for behaviors that should run before the sentence is spoken."""
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_pre_keywords
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if self.conversation_manager.transcriber.activation_name_exists(sentence, npc_keyword):
                    npc_contains_keyword = True
                    break
            for activation_sentence in behavior.activation_sentences:
                if activation_sentence.lower() in sentence.lower() or sentence.lower() in activation_sentence.lower():
                    npc_contains_keyword = True
                    break
            if npc_contains_keyword:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior._run(True, next_author, sentence=sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def post_sentence_evaluate(self,next_author, sentence): # Evaluates just the sentence, returns the behavior that was run
        """Evaluate the sentence for behaviors that should run after the sentence is spoken."""
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            npc_keywords = behavior.npc_post_keywords
            npc_contains_keyword = False
            for npc_keyword in npc_keywords:
                if npc_keyword in sentence or npc_keyword.lower() in sentence.lower():
                    npc_contains_keyword = True
                    break
            for activation_sentence in behavior.activation_sentences:
                if activation_sentence.lower() in sentence.lower() or sentence.lower() in activation_sentence.lower():
                    npc_contains_keyword = True
                    break
            if npc_contains_keyword:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior._run(True, next_author, sentence=sentence)
                    return behavior
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return None
    
    def get_behavior_summary(self):
        """Return a summary of all behaviors, and what they do.""" # TODO: Replace with a user editable template like message_format
        summary = ""
        for behavior in self.behaviors:
            if behavior.valid():
                if behavior.description is not None and not behavior.player_only:
                    summary += f"{behavior.description}\n"
                    if behavior.example is not None:
                        summary += f"Example: {behavior.example}"
                    summary += "\n"
        return summary
    
    def run_player_behaviors(self, sentence):
        """Run behaviors that are triggered by the player."""
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            if behavior.player or behavior.player_only:
                behavior.player_run(sentence)