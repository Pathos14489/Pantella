print("src/tokenizer.py")
from src.logging import logging
import os
import importlib
import json
logging.info("Imported required libraries in tokenizer.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")
    
Tokenizer_Types = {}
default = "tiktoken"

# Get all Tokenizers from src/tokenizers/ and add them to Tokenizer_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "tokenizers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned tokenizer: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.tokenizers")
        if module_name != "base_tokenizer":
            module = importlib.import_module(f"src.tokenizers.{module_name}")
            Tokenizer_Types[module.tokenizer_slug] = module

addons_path = os.path.join(os.path.dirname(__file__), "../", "addons/")
for addon_dir in os.listdir(addons_path):
    addon_path = os.path.join(addons_path, addon_dir)
    metadata_path = os.path.join(addon_path, "metadata.json")
    if os.path.isdir(addon_path) and os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            if metadata.get("enabled", False) == False:
                continue
    else:
        continue
    if os.path.isdir(addon_path) and os.path.exists(os.path.join(addon_path, "tokenizers/")):
        for file in os.listdir(os.path.join(addon_path, "tokenizers/")):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]
                if module_name in banned_modules:
                    logging.warning(f"Skipping banned tokenizer: {module_name}")
                    continue
                logging.info(f"Importing {module_name} from addons.{addon_dir}.tokenizers")
                module = importlib.import_module(f"addons.{addon_dir}.tokenizers.{module_name}")
                Tokenizer_Types[module.tokenizer_slug] = module
Tokenizer_Types["default"] = Tokenizer_Types[default] # This is a hack to make the default tokenizer work with any LLM that has a tokenizer_slug specified
logging.config(f"Available Tokenizers: {Tokenizer_Types.keys()}")
logging.info("Imported all tokenizers to Tokenizer_Types, ready to create a tokenizer object!")