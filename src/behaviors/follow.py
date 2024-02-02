import logging
import src.behaviors.base_behavior as base_behavior

class follow(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Follow"
        self.description = "If {player} asks you to follow them, and you are thoroughly convinced to do so, begin your response with 'Follow:'."
        self.example = "'Come with me if you want to live!' 'Follow: Alright, I'll follow you.'"
    
    def run(self, run=False, next_author=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Follow behavior called with no sentence!")
            else:
                logging.info(f"{next_author} is willing to follow someone.")
                self.manager.conversation_manager.game_state_manager.write_game_info('_mantella_aggro', '2') # TODO: Abstract this to a function
        return "follow"