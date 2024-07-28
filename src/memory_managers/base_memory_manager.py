from src.logging import logging

manager_slug = "base_memory_manager"

class base_MemoryManager():
    def __init__(self,character_manager):
        self.conversation_manager = character_manager.conversation_manager
        self.character_manager = character_manager
        self.config = self.conversation_manager.config
        self.conversation_history_directory = f"{self.conversation_manager.config.conversation_data_directory}/{self.config.game_id}/{self.conversation_manager.player_gender}_{self.conversation_manager.player_race}_{self.conversation_manager.player_name}/{self.gender}_{self.race}_{self.name}"
        if "base_id" in self.__dict__:
            self.conversation_history_directory += f"_{self.base_id}"
        if "ref_id" in self.__dict__:
            self.conversation_history_directory += f"_{self.ref_id}"
        self.conversation_history_directory += "/"

    @property
    def name(self):
        return self.character_manager.name
    
    @property
    def race(self):
        return self.character_manager.race
    
    @property
    def gender(self):
        return self.character_manager.gender
    
    @property
    def base_id(self):
        return self.character_manager.base_id
    
    @property
    def ref_id(self):
        return self.character_manager.ref_id

    @property
    def messages(self):
        return self.conversation_manager.messages

    def after_step(self):
        """Perform after dialogue generation in the memory manager - Some memory managers may need to perform some action every step"""
        logging.error("after_step() method not implemented in your memory manager.")
    
    def before_step(self):
        """Performed before dialogue generation in the memory manager - Some memory managers may need to perform some action every step"""
        logging.error("before_step() method not implemented in your memory manager.")
    
    def reached_conversation_limit(self):
        """Ran when the conversation limit is reached, or the conversation is ended - Some memory managers may need to perform some action when the conversation limit is reached"""
        logging.error("reached_conversation_limit() method not implemented in your memory manager.")
        input("Press enter to continue...")
        raise NotImplementedError("reached_conversation_limit() method not implemented in your memory manager.")
    
    def add_message(self, message):
        """Add a message to the memory manager"""
        logging.error("add_message() method not implemented in your memory manager.")
        input("Press enter to continue...")
        raise NotImplementedError("add_message() method not implemented in your memory manager.")
    
    def load_messages(self):
        """Load messages from the memory manager - Some memory managers may need to load messages from a file or database, and can also use this method to load old messages into the conversation_manager's messages"""
        logging.error("load_messages() method not implemented in your memory manager.")

    @property
    def memories(self):
        """Return a string representation of the memories stored in the memory manager - Some memory managers have updating memories strings"""
        logging.error("memories() method not implemented in your memory manager.")
        input("Press enter to continue...")
        raise NotImplementedError("memories() method not implemented in your memory manager.")
    
    @property
    def memory_offset(self):
        """Return the memory depth of the character"""
        logging.error("memory_offset() method not implemented in your memory manager.")
        input("Press enter to continue...")
        raise NotImplementedError("memory_offset() method not implemented in your memory manager.")
    
    @property
    def memory_offset_direction(self):
        """Return the memory offset direction of the character"""
        logging.error("memory_offset_direction() method not implemented in your memory manager.")
        input("Press enter to continue...")
        raise NotImplementedError("memory_offset_direction() method not implemented in your memory manager.")
        