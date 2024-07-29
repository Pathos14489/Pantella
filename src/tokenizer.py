print("src/tokenizer.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in tokenizer.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")
    
Tokenizer_Types = {}
default = "tiktoken"

# Get all Tokenizers from src/tokenizers/ and add them to Tokenizer_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "tokenizers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        logging.info(f"Importing {module_name} from src.tokenizers")
        if module_name in banned_modules:
            logging.warning(f"Skipping banned tokenizer: {module_name}")
            continue
        if module_name != "base_tokenizer":
            module = importlib.import_module(f"src.tokenizers.{module_name}")
            Tokenizer_Types[module.tokenizer_slug] = module
Tokenizer_Types["default"] = Tokenizer_Types[default] # This is a hack to make the default tokenizer work with any LLM that has a tokenizer_slug specified
logging.config(f"Available Tokenizers: {Tokenizer_Types.keys()}")
logging.info("Imported all tokenizers to Tokenizer_Types, ready to create a tokenizer object!")