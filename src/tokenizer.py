print("src/tokenizer.py")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in tokenizer.py")

Tokenizer_Types = {}
default = "tiktoken"

# Get all Tokenizers from src/tokenizers/ and add them to Tokenizer_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "tokenizers/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name != "base_tokenizer":
            module = importlib.import_module(f"src.tokenizers.{module_name}")
            Tokenizer_Types[module.tokenizer_slug] = module
Tokenizer_Types["default"] = Tokenizer_Types[default] # This is a hack to make the default tokenizer work with any LLM that has a tokenizer_slug specified
logging.info("Imported all tokenizers to Tokenizer_Types, ready to create a tokenizer object!")