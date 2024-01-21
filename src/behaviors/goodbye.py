import logging
import src.behaviors.base_behavior as base_behavior

class goodbye(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Goodbye"
        self.description = "If {player} says something that sounds like they're ending the conversation, or if you want to end the conversation with {player} begin your response with 'Goodbye:'."
        self.example = "'We should get going.' 'Goodbye: That's a good idea. Let's go.' 'Goodbye: I'm done talking to you.' 'Goodbye: Alright, thanks for the help. Goodbye.'"
        self.npc_keywords = ["goodbye", "bye", "farewell", "safe travels"]
    
    def run(self, run=False, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                logging.info(f"The NPC is saying goodbye.")
                self.manager.conversation_manager.end_conversation(self.conversation_manager.chat_manager.active_character) # Have the NPC saying the current voiceline end the conversation for themselves, and the player if no one else is talking to the player.
        return "Goodbye"