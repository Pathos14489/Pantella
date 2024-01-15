import src.tokenizers.openai_embedding_tokenizer as openai_embedding_tokenizer
import src.tokenizers.tiktoken_tokenizer as tiktoken_tokenizer

Tokenizer_Types = {
    "embedding": openai_embedding_tokenizer.Tokenizer, # Slow but good for compatibility with any model using the openai API
    "tiktoken": tiktoken_tokenizer.Tokenizer, # Fast but only works for specific models (Mainly OpenAI's models, but it should work for any model that uses the same tokenizer as OpenAI's models)
}