import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time

inference_engine_name = "chat_llm"

class base_LLM(base_LLM.base_LLM):
    def __init__(self, conversation_manager):
        global inference_engine_name
        super().__init__(conversation_manager)
        
    def get_context(self):
        return self.conversation_manager.get_context(True)