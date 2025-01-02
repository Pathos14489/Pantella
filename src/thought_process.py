print("Importing thought_process.py")
from src.logging import logging
import src.tokenizer as tokenizers
import os
import importlib
logging.info("Imported required libraries in thought_process.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

Thought_Types = {}
# Get all Thought models from src/thought_processes/ and add them to Thought_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "thought_processes/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned thought process: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.thought_processes")
        module = importlib.import_module(f"src.thought_processes.{module_name}")
        Thought_Types[module.thought_process_name] = module
logging.info("Imported all Thought models to Thought_Types!")

def create_thought_process(conversation_manager):
    logging.info(f"Creating Thought[{conversation_manager.config.thought_type}] object")
    thought_process = "default"
    if conversation_manager.config.thought_type not in Thought_Types and conversation_manager.config.thought_type != "default":
        logging.error(f"Could not find thought process: {conversation_manager.config.thought_type}! Please check your config.json file and try again!")
        thought_process = "none"
    thought_process = conversation_manager.config.thought_type
    if thought_process == "default":
        thought_process = "simple"
    if thought_process == "none":
        return None
    return Thought_Types[thought_process].ThoughtProcess