print("Importing koboldcpp.py...")
from src.logging import logging
import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import requests
logging.info("Imported required libraries in koboldcpp.py")

tokenizer_slug = "extras"
class Tokenizer(tokenizer.base_Tokenizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager, client):
        super().__init__(conversation_manager, tokenizer_slug)
        if not (self.config.inference_engine == "openai" or self.config.inference_engine == "default"):
            logging.error(f"extras tokenizer only works using a OpenAI API! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"extras tokenizer only works using a OpenAI API! Please check your config.json file and try again!")
        self.client = client # Unnecessary for this tokenizer, but it's here for compatibility with other openai tokenizers
        
    @utils.time_it
    def get_token_count(self, string):
        """Returns the number of tokens in the string"""
        url = self.config.alternative_openai_api_base.replace("/v1","") + "/extras/tokenize/count"
        data = {"input": string, "model": self.config.openai_model}
        r = requests.post(url, json=data).text
        num_tokens = int(r)
        return num_tokens
    