import logging
import src.behaviors.base_behavior as base_behavior

class add_to_conversation(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "AddToConversation"
        self.description = "If you want to talk to {player}, you can use this behavior to add them to the conversation."
        self.example = "'Do you want coffee?' 'AddToConversation: I'm not sure, me and {player} are in the middle of something. {player}, do you want coffee?'"
        self.radient_only = True
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"add_to_conversation behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character['name']} is adding {self.manager.conversation_manager.player_name} to the conversation.")
                self.manager.conversation_manager.game_state_manager.call_actor_method(speaker_character,"add_player_to_conversation") # .write_game_info('_mantella_aggro', '3') # TODO: Abstract this to a function
        return "add_to_conversation"