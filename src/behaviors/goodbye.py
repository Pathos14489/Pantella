from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class goodbye(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Goodbye"
        self.description = "If [player] is leaving or ending the conversation, or {name} wants to end the conversation, this behavior will be called."
        self.valid_games = ["skyrim","skyrimvr"]

    def run(self, speaker_character=None, sentence=None):
        logging.info(f"Behavior triggered: {self.keyword}")
        logging.info(f"{speaker_character.name} is leaving the conversation.")
        keywords = self.prompt_style["language"]["end_conversation_keywords"]
        for keyword in keywords:
            if keyword in sentence or keyword.lower() in sentence:
                speaker_character.leave_conversation()
                return
        speaker_character.leave_conversation()