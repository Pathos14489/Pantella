print("Importing tiktoken_tokenizer.py...")
from src.logging import logging
import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import tiktoken
logging.info("Imported required libraries in tiktoken_tokenizer.py")

tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class Tokenizer(tokenizer.base_Tokenizer): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,conversation_manager, client):
        super().__init__(conversation_manager)
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        self.client = client
        try:
            self.encoding = tiktoken.encoding_for_model(self.config.openai_model)
        except Exception as e:
            logging.error(f"Failed to load tiktoken encoding for model {self.config.openai_model}! Please check your config.json file and try again! If you're using a local model, try using the embedding tokenizer instead. It's slower, but more compatible.")
            logging.info("Loading default tokenizer instead...")
            self.encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')

    @utils.time_it
    def get_token_count(self, string):
        """Returns the number of tokens in the string"""
        tokens = self.encoding.encode(string)
        num_tokens = len(tokens)
        return num_tokens