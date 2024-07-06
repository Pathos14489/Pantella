print("Importing base_behavior_manager.py...")
from src.logging import logging
import random
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
    def behavior_style(self):
        """Return a list of all behavior styles."""
        return self.conversation_manager.config._behavior_style

    @property
    def behavior_keywords(self):
        """Return a list of all behavior keywords."""
        keywords = []
        for behavior in self.behaviors:
            if behavior.valid():
                if behavior.description is not None and not behavior.player_only:
                    keywords.append(behavior.keyword)
        return keywords
    
    def evaluate(self,  next_author, sentence): # Returns True if the keyword was found and the behavior was run, False otherwise
        """Evaluate the keyword for behaviors that should run."""
        logging.info(f"Evaluating sentence \"{sentence}\" for behaviors, next_author: {next_author}")
        sentence_words = sentence.split(" ")
        ran_behaviors = []
        for behavior in self.behaviors:
            rendered_behavior = self.render_behavior(behavior)
            if rendered_behavior in sentence_words:
                logging.info(f"Behavior triggered: {behavior.keyword}")
                try:
                    behavior._run(True, next_author, sentence=sentence)
                    ran_behaviors.append(behavior)
                except Exception as e:
                    logging.error(f"Error running behavior {behavior.keyword}: {e}")
        return ran_behaviors
    
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
    
    # def get_behavior_summary(self):
    #     """Return a summary of all behaviors, and what they do.""" # TODO: Replace with a user editable template like message_format
    #     summary = ""
    #     for behavior in self.behaviors:
    #         if behavior.valid():
    #             if behavior.description is not None and not behavior.player_only:
    #                 summary += f"{behavior.description}\n"
    #                 if behavior.example is not None:
    #                     summary += f"Example: {behavior.example}"
    #                 summary += "\n"
    #     return summary

    def get_behavior_memories(self, character):
        """Return a list of all behavior memories."""
        memories = []
        for behavior in self.behaviors:
            if behavior.valid() and not behavior.player_only:
                if behavior.description is not None and not behavior.player_only and behavior.examples is not None and len(behavior.examples) > 0:
                    random_example = random.choice(behavior.examples)
                    for message in random_example:
                        if message["role"] == "assistant":
                            message["name"] = character.name
                        message["content"] = message["content"].replace("{command}",self.render_behavior(behavior))
                        memories.append(message)
        return memories
    
    def render_behavior(self, behavior):
        """Render a behavior."""
        behavior_style = self.conversation_manager.config._behavior_style
        behavior_string = behavior_style["behavior_format"]
        behavior_string = behavior_string.replace("[prefix]",behavior_style["prefix"])
        behavior_string = behavior_string.replace("[behavior_name]",behavior.keyword)
        behavior_string = behavior_string.replace("[suffix]",behavior_style["suffix"])
        return behavior_string
        
    def run_player_behaviors(self, sentence):
        """Run behaviors that are triggered by the player."""
        logging.info(f"Evaluating sentence {sentence}")
        for behavior in self.behaviors:
            if behavior.player or behavior.player_only:
                behavior.player_run(sentence)