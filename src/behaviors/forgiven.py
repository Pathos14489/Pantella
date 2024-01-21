import logging
import src.behaviors.base_behavior as base_behavior

class forgiven(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Forgiven"
        self.description = "If {player} renounces their words, or to end combat, begin your response with 'Forgiven:'."
        self.example = "'I'm sorry, I didn't mean it!' 'Forgiven: Alright, I'll forgive you.'"
        self.npc_keywords = []
    
    def run(self, run=False, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                logging.info(f"The player made up with the NPC")
                self.manager.conversation_manager.game_state_manager.write_game_info('_mantella_aggro', '0')
        return "forgiven"