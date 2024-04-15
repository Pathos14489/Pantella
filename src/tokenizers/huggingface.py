print("Importing huggingface.py...")
from src.logging import logging
import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
logging.info("Imported required libraries in huggingface.py")
try:
    from transformers import AutoTokenizer
    loaded = True
except Exception as e:
    loaded = False
tokenizer_slug = "huggingface"
class Tokenizer(tokenizer.base_Tokenizer): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,conversation_manager):
        if not loaded:
            logging.error(f"Failed to load transformers, so huggingface tokenizer cannot be used! Please check that you have installed it correctly.")
            input("Press enter to continue...")
            raise ValueError(f"Failed to load transformers, so huggingface tokenizer cannot be used! Please check that you have installed it correctly.")
        super().__init__(conversation_manager)
        self.tokenizer_slug = tokenizer_slug
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.llm)

    @utils.time_it
    def get_token_count(self, string):
        """Returns the number of tokens in the string"""
        tokens = self.tokenizer.encode(string)
        num_tokens = len(tokens)
        return num_tokens