import logging

class BaseBehavior():
    def __init__(self, manager):
        self.manager = manager
        self.keyword = None
        self.description = None
        self.example = None
        self.radient_only = False
        self.non_radient_only = False
        self.single_npc_with_npc_only = False
        self.single_npc_with_player_only = False
        self.multi_npc_only = False
        self.npc_pre_keywords = [] # Keywords that the NPC can say that will trigger this behavior before generating the voiceline
        self.npc_post_keywords = [] # Keywords that the NPC can say that will trigger this behavior after generating the voiceline

    @property
    def conversation_manager(self):
        return self.manager.conversation_manager
    
    def run(self, run=False, next_author=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Goodbye behavior called with no sentence!")
            else:
                pass
        logging.error("BaseBehavior run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return "BASEBEHAVIOR"
    
    def valid(self):
        if not self.conversation_manager.radient_dialogue and self.radient_only:
            return False
        if not self.conversation_manager.radient_dialogue and self.non_radient_only:
            return False
        conversation_type = self.conversation_manager.get_conversation_type() # single_npc_with_npc, single_npc_with_player, multi_npc
        if conversation_type == "single_npc_with_npc" and (self.single_npc_with_player_only or self.multi_npc_only): # If the conversation type is single_npc_with_npc, and the behavior is single_npc_with_player_only or multi_npc_only, skip this behavior
            return False
        if conversation_type == "single_npc_with_player" and (self.single_npc_with_npc_only or self.multi_npc_only): # If the conversation type is single_npc_with_player, and the behavior is single_npc_with_npc_only or multi_npc_only, skip this behavior
            return False
        if conversation_type == "multi_npc" and (self.single_npc_with_npc_only or self.single_npc_with_player_only): # If the conversation type is multi_npc, and the behavior is single_npc_with_npc_only or single_npc_with_player_only, skip this behavior
            return False
        return True