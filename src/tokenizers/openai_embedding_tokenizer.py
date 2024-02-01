import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import logging
tokenizer_slug = "embedding"
class Tokenizer(tokenizer.base_Tokenizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager, client):
        super().__init__(conversation_manager)
        if not (self.config.inference_engine == "openai" or self.config.inference_engine == "default"):
            logging.error(f"Embedding tokenizer only works with OpenAI's API! Please check your config.json file and try again!")
            input("Press enter to continue...")
            exit()
        self.tokenizer_slug = tokenizer_slug
        self.client = client
        
    @utils.time_it
    def get_token_count(self, string):
        embedding = self.client.embeddings.create(
            model=self.config.llm,
            input=string
        )
        num_tokens = int(embedding.usage.prompt_tokens)
        return num_tokens