print("Importing base_behavior_manager.py...")
from src.logging import logging
import random
import os
logging.info("Imported required libraries in base_behavior_manager.py")

default_behaviors_dir =  os.path.join(os.path.dirname(os.path.abspath(__file__)),"../behaviors/")

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
manager_slug = "default_behavior_manager"

class BehaviorManager():
    def __init__(self,conversation_manager):
        self.conversation_manager = conversation_manager
        self.behaviors = []
        self.named_behaviors = {}
        logging.info("Loading default behaviors...")
        self.load_behaviors(default_behaviors_dir)
        logging.info("Loading addon behaviors...")
        for addon_slug in self.conversation_manager.config.addons:
            addon = self.conversation_manager.config.addons[addon_slug]
            if addon["enabled"] and "behaviors" in addon["addon_parts"]:
                logging.info(f"Loading behaviors from addon '{addon_slug}'...")
                self.load_behaviors(os.path.abspath(os.path.join(self.conversation_manager.config.addons_dir,addon_slug,"behaviors")),addon_slug)

        logging.info(f"Loaded default behavior manager with {len(self.behaviors)} behaviors")

    def load_behaviors(self,behaviors_dir, addon_slug = None):
        for filename in os.listdir(behaviors_dir):
            if filename == "base_behavior.py":
                continue
            if filename.endswith(".py") and not filename.startswith("__"):
                # logging.info("Loading behavior " + filename)
                behavior_name = filename.split(".py")[0]
                if addon_slug is None:
                    behavior = __import__("src.behaviors." + behavior_name, fromlist=["Behavior"])
                    print(behavior)
                else:
                    behavior = __import__("addons." + addon_slug + ".behaviors." + behavior_name, fromlist=["Behavior"])
                    print(behavior)
                behavior = getattr(behavior, "Behavior")(self)
                # logging.info(behavior)
                if self.conversation_manager.config.game_id in behavior.valid_games:
                    logging.config(f"Behavior '{behavior_name}' supported by game '{self.conversation_manager.config.game_id}'")
                else:
                    logging.config(f"Behavior '{behavior_name}' not supported by game '{self.conversation_manager.config.game_id}'")
                    continue
                if behavior._run(False) == "BASEBEHAVIOR":
                    logging.error("BaseBehavior run() called for " + behavior_name + ", this should be overwritten by the child class!")
                else:
                    # logging.info("Loaded behavior " + filename)
                    self.behaviors.append(behavior)
                    self.named_behaviors[behavior_name] = behavior

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
    
    def evaluate(self, possible_word, next_author, sentence): # Returns True if the keyword was found and the behavior was run, False otherwise
        """Evaluate the keyword for behaviors that should run."""
        logging.info(f"Evaluating sentence \"{sentence}\" for behaviors, next_author: {next_author}")
        ran_behaviors = []
        for behavior in self.behaviors:
            rendered_behavior = self.render_behavior(behavior)
            if rendered_behavior == possible_word:
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
    
    def get_behavior_summary(self, character):
        """Return a summary of all behaviors, and what they do.""" # TODO: Replace with a user editable template like message_format
        summary = ""
        for behavior in self.behaviors:
            if behavior.valid():
                if behavior.player_only:
                    continue
                if character is None or (behavior.guard_only and not character.is_guard):
                    continue
                if behavior.description is not None and behavior.description != "":
                    summary += f"{behavior.description}\n\n".replace("{command}",self.render_behavior(behavior))
        summary = summary.strip()
        return summary

    def get_behavior_memories(self, character):
        """Return a list of all behavior memories."""
        memories = []
        for behavior in self.behaviors:
            try:
                if behavior.valid() and not behavior.player_only:
                    if behavior.player_only:
                        continue
                    if character is None or (behavior.guard_only and not character.is_guard):
                        continue
                    if behavior.description is not None and behavior.examples is not None and len(behavior.examples) > 0:
                        random_example = random.choice(behavior.examples)
                        for message in random_example:
                            if message["role"] == "assistant":
                                message["name"] = character.name
                            message["content"] = message["content"].replace("{command}",self.render_behavior(behavior))
                            memories.append(message)
            except Exception as e:
                logging.error(f"Behavior: {behavior}")
                logging.error(f"Character: {character}")
                logging.error(f"Behavior valid: {behavior.valid()}")
                logging.error(f"Behavior player only: {behavior.player_only}")
                logging.error(f"Behavior guard only: {behavior.guard_only}")
                logging.error(f"Behavior description: {behavior.description}")
                logging.error(f"Behavior examples: {behavior.examples}")
                logging.error(f"Error getting behavior memories for {behavior.keyword}: {e}")
                raise e
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