import logging
import src.character_manager as character_manager # Character class
import src.utils as utils
class Characters:
    def __init__(self, conversation_manager):
        self.active_characters = {}
        self.conversation_manager = conversation_manager

    @property
    def active_characters_list(self): # Returns a list of all active characters
        characters = []
        for character in self.active_characters:
            characters.append(self.active_characters[character])
        return characters
    
    @property
    def bios(self): # Returns a paragraph comprised of all active characters bios
        bios = ""
        for character in self.active_characters_list:
            bios += character.bio
            if character != self.active_characters_list[-1]:
                bios += "\n\n"
        logging.info("Active Bios: " + bios)
        return bios
    
    @property
    def names(self): # Returns a list of all active characters names
        return [character.name for character in self.active_characters_list]
    
    @property
    def names_w_player(self): # Returns a list of all active characters names with the player's name included
        names = self.names
        names.append(self.conversation_manager.player_name)
        return names
    
    @property
    def relationship_summary(self): # Returns a paragraph comprised of all active characters relationship summaries
        if len(self.active_characters) == 0:
            logging.warning("No active characters, returning empty relationship summary")
            return ""
        if len(self.active_characters) == 1:
            logging.info("Only one active character, returning SingleNPC style relationship summary")
            perspective_player_name, perspective_player_description, trust = self.active_characters_list[0].get_perspective_player_identity()
            relationship_summary = perspective_player_description
        else:
            logging.info("Multiple active characters, returning MultiNPC style relationship summary")
            relationship_summary = ""
            for character in self.active_characters_list:
                perspective_player_name, perspective_player_description, trust = character.get_perspective_player_identity()
                relationship_summary += perspective_player_description
                if character != self.active_characters_list[-1]:
                    relationship_summary += "\n\n"
        logging.info("Active Relationship Summary: " + relationship_summary)
        return relationship_summary

    @property
    def conversation_summaries(self): # Returns a paragraph comprised of all active characters conversation summaries
        if len(self.active_characters) == 0:
            logging.warning("No active characters, returning empty conversation summaries")
            return ""
        if len(self.active_characters) == 1:
            logging.info("Only one active character, returning SingleNPC style conversation summaries")
            conversation_summaries = self.active_characters_list[0].conversation_summary
        else:
            logging.info("Multiple active characters, returning MultiNPC style conversation summaries")
            conversation_summaries = "The following is a summary of the conversation so far. If there is nothing here, it means these characters do not have a history of conversation:\n"
            for character in self.active_characters_list:
                conversation_summaries += character.conversation_summary
                if character != self.active_characters_list[-1]:
                    conversation_summaries += "\n\n"

    @property
    def replacement_dict(self): # Returns a dictionary of replacement values for the current context -- Dynamic Variables
        if len(self.active_characters) == 1 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
            replacement_dict = self.active_characters_list[0].replacement_dict
            replacement_dict2 = self.active_characters_list[1].replacement_dict
            replacement_dict2 = {}
            for key in replacement_dict:
                replacement_dict2[key + "2"] = replacement_dict[key]
            replacement_dict.update(replacement_dict2)
        elif len(self.active_characters) == 1 and not self.conversation_manager.radiant_dialogue: # SingleNPCw/Player style context
            replacement_dict = self.active_characters_list[0].replacement_dict
        else: # MultiNPC style context
            replacement_dict = {
                "conversation_summaries": self.conversation_summaries,
                "names": ", ".join(self.names),
                "names_w_player": ", ".join(self.names_w_player),
                "relationship_summary": self.relationship_summary,
                "bios": self.bios,
            }
        
        if self.conversation_manager.current_in_game_time is not None: # If in-game time is available, add in-game time properties to replacement_dict
            time_group = utils.get_time_group(self.conversation_manager.current_in_game_time["hour24"]) # get time group from in-game time before 12/24 hour conversion
            for time_property in self.conversation_manager.current_in_game_time: # Add in-game time properties to replacement_dict
                replacement_dict[time_property] = self.conversation_manager.current_in_game_time[time_property]
        else:
            logging.warning("No in-game time available when generating replacement_dict, returning empty time properties")
        replacement_dict["time_group"] = time_group
        replacement_dict["location"] = self.conversation_manager.current_location
        replacement_dict["player_name"] = self.conversation_manager.player_name
        replacement_dict["player_race"] = self.conversation_manager.player_race
        replacement_dict["player_gender"] = self.conversation_manager.player_gender
        replacement_dict["behavior_summary"] = self.conversation_manager.behavior_manager.get_behavior_summary()
        replacement_dict["language"] = self.conversation_manager.language_info['language']

        
        if "bio" in replacement_dict: # If bio is in replacement_dict, add bio2 and bios to replacement_dict
            replacement_dict["bio"] = replacement_dict["bio"].format(**replacement_dict)
        if "bio2" in replacement_dict:
            replacement_dict["bio2"] = replacement_dict["bio2"].format(**replacement_dict)
        if "bios" in replacement_dict:
            replacement_dict["bios"] = replacement_dict["bios"].format(**replacement_dict)

        return replacement_dict

    def active_character_count(self): # Returns the number of active characters as an int
        return len(self.active_characters)
    
    def get_raw_prompt(self):
        if len(self.active_characters) == 1 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
            logging.info("Two active characters, but player isn't in conversation, returning SingleNPCw/NPC style context")
            prompt = self.conversation_manager.config.single_npc_with_npc_prompt
        elif len(self.active_characters) == 1 and not self.conversation_manager.radiant_dialogue:
            logging.info("Only one active character, returning SingleNPCw/Player style context")
            prompt = self.conversation_manager.config.single_player_with_npc_prompt
        else:
            logging.info("Multiple active characters, returning MultiNPC style context")
            prompt = self.conversation_manager.config.multi_npc_prompt
        return prompt

    def get_system_prompt(self): # Returns the current context for the given active characters as a string
        if len(self.active_characters) == 0:
            logging.warning("No active characters, returning empty context")
            return ""

        prompt = self.get_raw_prompt()

        system_prompt = prompt.format(**self.replacement_dict)
        # logging.info("System Prompt: " + system_prompt)
        return system_prompt

    def get_character(self, info, is_generic_npc=False):
        character = character_manager.Character(self, info, is_generic_npc)
        return character