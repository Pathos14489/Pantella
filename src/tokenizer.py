import os
import sys
from src.logging import logging
import importlib

# Tokenizer_Types = {
#     "embedding": openai_embedding_tokenizer.Tokenizer, # Slow but good for compatibility with any model using the openai API
#     "tiktoken": tiktoken_tokenizer.Tokenizer, # Fast but only works for specific models (Mainly OpenAI's models, but it should work for any model that uses the same tokenizer as OpenAI's models)
# }
# LLM_Types = {}
# # Get all LLMs from src/llms/ and add them to LLM_Types
# for file in os.listdir("src/llms/"):
#     if file.endswith(".py") and not file.startswith("__"):
#         module_name = file[:-3]
#         if module_name != "base_llm":
#             module = importlib.import_module(f"src.llms.{module_name}")
#             LLM_Types[module.inference_engine_name] = module    
# LLM_Types["default"] = LLM_Types[defalut]
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