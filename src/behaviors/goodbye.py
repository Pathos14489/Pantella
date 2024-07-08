from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class goodbye(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Goodbye"
        self.description = "If {perspective_player_name} is leaving or ending the conversation, this behavior will be called."
        self.npc_post_keywords = self.conversation_manager.config.language["end_conversation_keywords"] # TODO: Reimplement this with new per-character language tracking for end_conversation_keywords
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is leaving the conversation.")
        speaker_character.leave_conversation()