print("Importing src.characters_manager.py")
from src.logging import logging
import src.character_manager as character_manager # Character class
import src.utils as utils
logging.info("Imported required libraries in characters_manager.py")

class CharacterDoesNotExist(Exception):
    """Exception raised when NPC name cannot be found in characterDB"""
    pass

class Characters:
    def __init__(self, conversation_manager):
        self.active_characters = {}
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config

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
    def replacement_dict(self): # Returns a dictionary of replacement values for the current context -- Dynamic Variables
        if len(self.active_characters) == 1 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
            replacement_dict = self.active_characters_list[0].replacement_dict
        elif len(self.active_characters) == 1 and not self.conversation_manager.radiant_dialogue: # SingleNPCw/Player style context
            replacement_dict = self.active_characters_list[0].replacement_dict
        elif len(self.active_characters) == 2 and self.conversation_manager.radiant_dialogue: # TwoNPC no player style context
            replacement_dicts = [c.replacement_dict for c in self.active_characters_list]
            # number the variables in the replacement_dicts
            replacement_dicts = [{f"{k}{i+1}": v for k, v in replacement_dicts[i].items()} for i in range(len(replacement_dicts))]
            # combine the replacement_dicts
            replacement_dict = {k: v for d in replacement_dicts for k, v in d.items()}
            replacement_dict["language"] = self.conversation_manager.language_info['language']
            replacement_dict["perspective_player_name"] = self.conversation_manager.player_name
            print(replacement_dict)
        else: # MultiNPC style context
            replacement_dict = {
                "names": ", ".join(self.names),
                "names_w_player": ", ".join(self.names_w_player),
                "perspective_player_name": self.conversation_manager.player_name,
                "relationship_summary": self.relationship_summary,
                "bios": self.bios,
                "langage": self.conversation_manager.language_info['language']
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
        replacement_dict["behavior_summary"] = self.conversation_manager.behavior_manager.get_behavior_summary() # Add behavior summary to replacement_dict and format it using replacement_dict before doing so
        if "name" in replacement_dict: # If name is in replacement_dict, add name2 and names to replacement_dict
            replacement_dict["behavior_summary"] = replacement_dict["behavior_summary"].format(**replacement_dict)
        else:
            replacement_dict["behavior_summary"] = replacement_dict["behavior_summary"].replace("{name}", "{name1}")
            for name in self.names:
                replacement_dict["name"+str(self.names.index(name)+1)] = name
            replacement_dict["behavior_summary"] = replacement_dict["behavior_summary"].format(**replacement_dict)
        replacement_dict["behavior_keywords"] = ", ".join(self.conversation_manager.behavior_manager.behavior_keywords)

        
        if "bio" in replacement_dict: # If bio is in replacement_dict, add bio2 and bios to replacement_dict
            replacement_dict["bio"] = replacement_dict["bio"].replace("{bio}", "").format(**replacement_dict)
        if "bio2" in replacement_dict:
            replacement_dict["bio2"] = replacement_dict["bio2"].replace("{bio2}", "").format(**replacement_dict)
        if "bios" in replacement_dict:
            replacement_dict["bios"] = replacement_dict["bios"].replace("{bios}", "").format(**replacement_dict)

        if "language" not in replacement_dict:
            replacement_dict["language"] = self.conversation_manager.language_info['language']

        replacement_dict["context"] = ""
        context_string = self.conversation_manager.game_interface.get_current_context_string()
        if context_string is not None and context_string != "":
            replacement_dict["context"] = context_string

        return replacement_dict

    def active_character_count(self): # Returns the number of active characters as an int
        return len(self.active_characters)
    
    def get_raw_prompt(self):
        prompt_style = self.conversation_manager.config._prompt_style
        logging.info(prompt_style)
        if len(self.active_characters) == 1 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
            logging.info("One active characters, but player isn't in conversation, waiting for another character to join the conversation...")
            prompt = prompt_style["single_player_with_npc_prompt"] # TODO: Custom prompt for single NPCs by themselves starting a topic?
        elif len(self.active_characters) == 1 and not self.conversation_manager.radiant_dialogue:
            logging.info("Only one active character, returning SingleNPCw/Player style context")
            prompt = prompt_style["single_player_with_npc_prompt"]
        elif len(self.active_characters) == 2 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
            logging.info("Two active characters, but player isn't in conversation, returning SingleNPCw/NPC style context")
            prompt = prompt_style["single_npc_with_npc_prompt"]
        else:
            logging.info("Multiple active characters, returning MultiNPC style context")
            prompt = prompt_style["multi_npc_prompt"]
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
    
    def add_message(self,msg):
        for character in self.active_characters_list:
            character.add_message(msg)
    
    def remove_from_conversation(self, character):
        if character.name in self.active_characters:
            del self.active_characters[character.name]
        else:
            logging.warning(f"Character {character.name} not in active characters list, cannot remove from conversation.")
    
    def step(self):
        for character in self.active_characters_list:
            character.step()

    def reached_conversation_limit(self):
        for character in self.active_characters_list:
            character.reached_conversation_limit()

    def get_memories(self):
        memories = []
        for character in self.active_characters_list:
            memories.extend(character.memories)
        memories.append({
            "role": self.config.system_name,
            "content": "The rest of the messages below this are from the current conversation, the present. Everything above this is a memory from the past."
        })
        return memories
    
    @property
    def memory_offset(self):
        """Return the memory depth of the character"""
        return self.active_characters_list[0].memory_manager.memory_offset

    @property
    def memory_offset_direction(self):
        """Return the memory offset direction of the character"""
        return self.active_characters_list[0].memory_manager.memory_offset_direction