import logging
import src.behaviors.base_behavior as base_behavior

class barter(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Barter"
        self.description = "If {player} wants to barter with {name}, and {name} wants to barter with them, {name} will begin their response with 'Barter:'."
        self.example = "'Hey, can I sell you something?' 'Barter: Sure, what do you have?' or 'Hey, can I buy something from you?' 'Barter: Sure, what do you want?'"
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Barter behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to barter.")
                self.queue_actor_method(speaker_character,"Wait","2")
                self.new_game_event(f"*{speaker_character.name} started bartering with {self.manager.conversation_manager.player_name}.*\n")
                self.queue_actor_method(speaker_character,"OpenBarterMenu")
        return "barter"
    