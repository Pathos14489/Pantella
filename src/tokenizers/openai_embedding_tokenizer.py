import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
class Tokenizer(tokenizer.base_Tokenizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self,config, client):
        super().__init__(config)
        self.client = client
        
    @utils.time_it
    def get_token_count(self, string):
        embedding = self.client.embeddings.create(
            model=self.config.llm,
            input=string
        )
        num_tokens = int(embedding.usage.prompt_tokens)
        return num_tokens