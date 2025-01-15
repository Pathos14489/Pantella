print("Importing src.characters_manager.py")
from src.logging import logging
import src.character_manager as character_manager # Character class
import src.utils as utils
import random
logging.info("Imported required libraries in characters_manager.py")

class CharacterDoesNotExist(Exception):
    """Exception raised when NPC name cannot be found in characterDB"""
    pass

class Characters:
    """Characters Manager Class - Manages all active characters in the conversation"""
    def __init__(self, conversation_manager):
        logging.info("Creating Characters Manager")
        self.active_characters = {}
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.character_manager_class = character_manager.create_character_manager(self.config)
        logging.info("Characters Manager created")

    @property
    def active_characters_list(self): # Returns a list of all active characters
        """Return a list of all active characters"""
        characters = []
        for character in self.active_characters:
            characters.append(self.active_characters[character])
        return characters
    
    @property
    def bios(self): # Returns a paragraph comprised of all active characters bios
        """Return a paragraph comprised of all active characters bios"""
        bios = ""
        for character in self.active_characters_list:
            bios += character.bio
            if character != self.active_characters_list[-1]:
                bios += "\n\n"
        logging.info("Active Bios: " + bios)
        return bios
    
    @property
    def names(self): # Returns a list of all active characters names
        """Return a list of all active characters names"""
        return [character.name for character in self.active_characters_list]
    
    @property
    def names_w_player(self): # Returns a list of all active characters names with the player's name included
        """Return a list of all active characters names with the player's name included"""
        names = self.names
        names.append(self.conversation_manager.player_name)
        return names
    
    @property
    def relationship_summary(self): # Returns a paragraph comprised of all active characters relationship summaries
        """Return a paragraph comprised of all active characters relationship summaries"""
        if len(self.active_characters) == 0:
            logging.warning("No active characters, returning empty relationship summary")
            return ""
        if len(self.active_characters) == 1:
            logging.info("Only one active character, returning SingleNPC style relationship summary")
            perspective_player_name, trust = self.active_characters_list[0].get_perspective_player_identity()
            relationship_summary = perspective_player_name
        else:
            logging.info("Multiple active characters, returning MultiNPC style relationship summary")
            relationship_summary = ""
            for character in self.active_characters_list:
                perspective_player_name, trust = character.get_perspective_player_identity()
                relationship_summary += perspective_player_name
                if character != self.active_characters_list[-1]:
                    relationship_summary += "\n\n"
        logging.info("Active Relationship Summary: " + relationship_summary)
        return relationship_summary

    @property
    def prompt_style(self):
        """Return the prompt style for the current conversation"""
        conversation_type = self.conversation_manager.get_conversation_type()
        prompt_style = self.config._prompt_style
        if conversation_type == "single_player_with_npc_prompt": # SingleNPCw/Player style context
            prompt_style = self.active_characters_list[0].prompt_style
        else:
            try:
                prompt_style = random.choice([c.prompt_style for c in self.active_characters_list])
            except Exception as e:
                # logging.error(f"Error getting prompt style: {e}")
                prompt_style = self.config._prompt_style["style"]
        # logging.info("Prompt Style:", prompt_style)
        return prompt_style
    
    @property
    def language(self):
        """Return the language for the current conversation"""
        conversation_type = self.conversation_manager.get_conversation_type()
        language = self.config._prompt_style['language']
        if conversation_type == "single_player_with_npc_prompt": # SingleNPCw/Player style context
            language = self.active_characters_list[0].language
        # logging.info("Language:", language["language_name"] + "("+language["language_code"]+")")
        return language
        
    @property
    def replacement_dict(self): # Returns a dictionary of replacement values for the current context -- Dynamic Variables
        """Return a dictionary of replacement values for the current context"""
        conversation_type = self.conversation_manager.get_conversation_type()
        if conversation_type == "single_player_with_npc": # TwoNPC no player style context
            logging.info("SingleNPCw/Player style context, returning replacement_dict from active character")
            replacement_dict = self.active_characters_list[0].replacement_dict
        elif conversation_type == "single_npc_with_npc": # MultiNPC style context
            logging.info("SingleNPCw/NPC style context, returning replacement_dict from active characters")
            replacement_dicts = [c.replacement_dict for c in self.active_characters_list]
            # number the variables in the replacement_dicts
            replacement_dicts = [{f"{k}{i+1}": v for k, v in replacement_dicts[i].items()} for i in range(len(replacement_dicts))]
            # combine the replacement_dicts
            replacement_dict = {k: v for d in replacement_dicts for k, v in d.items()}
            replacement_dict["language"] = self.language["in_game_language_name"]
            replacement_dict["perspective_player_name"] = self.conversation_manager.player_name
        elif conversation_type == "multi_npc": # MultiNPC style context
            logging.info("MultiNPC style context, returning replacement_dict from active characters")
            replacement_dict = {
                "names": ", ".join(self.names),
                "names_w_player": ", ".join(self.names_w_player),
                "perspective_player_name": self.conversation_manager.player_name,
                "relationship_summary": self.relationship_summary,
                "bios": self.bios,
                "langage": self.language["in_game_language_name"],
            }
        else:
            logging.warning("Could not determine conversation type, returning empty replacement_dict")
            return {}
        
        if self.conversation_manager.current_in_game_time is not None: # If in-game time is available, add in-game time properties to replacement_dict
            time_group = utils.get_time_group(self.conversation_manager.current_in_game_time["hour24"]) # get time group from in-game time before 12/24 hour conversion
            for time_property in self.conversation_manager.current_in_game_time: # Add in-game time properties to replacement_dict
                replacement_dict[time_property] = self.conversation_manager.current_in_game_time[time_property]
            replacement_dict["time_group"] = time_group
        else:
            logging.warning("No in-game time available when generating replacement_dict, returning empty time properties")
            replacement_dict["time_group"] = "unknown"
            replacement_dict["hour24"] = "??:??"
            replacement_dict["hour12"] = "??:?? ??"
            replacement_dict["minute"] = "??"
            replacement_dict["second"] = "??"
            replacement_dict["day"] = "??"
            replacement_dict["month"] = "??"
            replacement_dict["year"] = "????"
        replacement_dict["location"] = self.conversation_manager.current_location
        replacement_dict["player_name"] = self.conversation_manager.player_name
        replacement_dict["player_race"] = self.conversation_manager.player_race
        replacement_dict["player_gender"] = self.conversation_manager.player_gender
        replacement_dict["behavior_summary"] = self.conversation_manager.behavior_manager.get_behavior_summary(self.active_characters_list[0]) # Add behavior summary to replacement_dict and format it using replacement_dict before doing so # TODO: Make this work better for multi character conversations
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
            replacement_dict["language"] = self.prompt_style["language"]["in_game_language_name"]

        replacement_dict["context"] = ""
        context_string = self.conversation_manager.game_interface.get_current_context_string()
        if context_string is not None and context_string != "":
            replacement_dict["context"] = context_string.format(**replacement_dict)

        logging.info("Replacement Dict: ", replacement_dict)
        return replacement_dict

    def render_game_event(self,line:str):
        """Render a game event line using the language file"""
        try:
            if line.startswith("player<"):
                line_2 = line.split("<",1)[1]
                game_event_title, args_strings  = line_2.split(">",1)
                args = args_strings.split("|")
                args_dict = {}
                for arg in args:
                    key, value = arg.split("=")
                    args_dict[key] = value
                line = self.language["game_events"]["player"][game_event_title].format(**args_dict)
            elif line.startswith("npc<"):
                line_2 = line.split("<",1)[1]
                game_event_title, args_strings  = line_2.split(">",1)
                args = args_strings.split("|")
                args_dict = {}
                for arg in args:
                    args = arg.split("=")
                    if len(args) == 1:
                        key = args[0]
                        value = ""
                    else:
                        key, value = arg.split("=")
                    args_dict[key] = value
                line = self.language["game_events"]["npc"][game_event_title].format(**args_dict)
        except Exception as e:
            logging.error(f"Error rendering game event: {line} - {e}")
            raise e
        return line

    def active_character_count(self): # Returns the number of active characters as an int
        """Return the number of active characters as an int"""
        return len(self.active_characters)
    
    def get_raw_prompt(self):
        """Return the current context for the given active characters as a string"""
        # prompt_style = self.conversation_manager.config._prompt_style["style"]
        # logging.info(prompt_style)
        # if len(self.active_characters) == 1 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
        #     logging.info("One active characters, but player isn't in conversation, waiting for another character to join the conversation...")
        #     prompt = prompt_style["single_player_with_npc_prompt"] # TODO: Custom prompt for single NPCs by themselves starting a topic?
        # elif len(self.active_characters) == 1 and not self.conversation_manager.radiant_dialogue:
        #     logging.info("Only one active character, returning SingleNPCw/Player style context")
        #     prompt = prompt_style["single_player_with_npc_prompt"]
        # elif len(self.active_characters) == 2 and self.conversation_manager.radiant_dialogue: # SingleNPC style context
        #     logging.info("Two active characters, but player isn't in conversation, returning SingleNPCw/NPC style context")
        #     prompt = prompt_style["single_npc_with_npc_prompt"]
        # else:
        #     logging.info("Multiple active characters, returning MultiNPC style context")
        #     prompt = prompt_style["multi_npc_prompt"]
        # return prompt
        conversation_type = self.conversation_manager.get_conversation_type()
        if conversation_type != "none":
            return self.language["prompts"][conversation_type]
        else:
            logging.warning("No active characters, returning empty context")
            return ""

    def get_system_prompt(self): # Returns the current context for the given active characters as a string
        """Return the current context for the given active characters as a string"""
        if len(self.active_characters) == 0:
            logging.warning("No active characters, returning empty context")
            return ""

        prompt = self.get_raw_prompt()
        
        system_prompt = prompt.format(**self.replacement_dict)
        # logging.info("System Prompt: " + system_prompt)
        return system_prompt

    def get_character(self, info):
        """Return a character object from the current character manager"""
        character = self.character_manager_class(self, info)
        return character
    
    def add_message(self,msg):
        """Add a message to all active characters"""
        for character in self.active_characters_list:
            character.add_message(msg)
    
    def remove_from_conversation(self, character):
        """Remove a character from the conversation"""
        if character.name in self.active_characters:
            del self.active_characters[character.name]
        else:
            logging.warning(f"Character {character.name} not in active characters list, cannot remove from conversation.")
    
    def after_step(self):
        """Perform an after step in the memory manager - Some memory managers may need to perform some action every step"""
        for character in self.active_characters_list:
            character.after_step()

    def before_step(self):
        """Perform a before step in the memory manager - Some memory managers may need to perform some action every step"""
        for character in self.active_characters_list:
            character.after_step()

    def reached_conversation_limit(self):
        """Perform an end of conversation step in the memory manager - Some memory managers may need to perform some action every step"""
        for character in self.active_characters_list:
            character.reached_conversation_limit()

    def get_memories(self):
        """Return the memories for the current conversation"""
        memories = []
        random_character = random.choice(self.active_characters_list)
        name_insert = random_character.name
        if self.language["behavior_example_insertion"]:
            memories.append({
                "role": self.config.system_name,
                "content": self.language["behaviors_explanation_system_message_1"],
                "type": "prompt"
            })
            behavior_memories = self.conversation_manager.behavior_manager.get_behavior_memories(random_character) # TODO: Check if this works fine, and if it's the right way to do it. Might need to redo how this works
            for fake_memory in behavior_memories:
                fake_memory["content"] = fake_memory["content"].replace("{name}",name_insert)
                memories.append(fake_memory)
        if self.language["include_behavior_explanation"]:
            memories.append({
                "role": self.config.system_name,
                "content": self.language["behaviors_explanation_system_message_2"].replace("{summaries}",self.conversation_manager.behavior_manager.get_behavior_summary(random_character)).replace("{name}",name_insert),
                "type": "prompt"
            })
        for character in self.active_characters_list:
            memories.extend(character.memories)
        memories.append({
            "role": self.config.system_name,
            "content": self.language["memory_present_separator"].replace("{name}",name_insert),
            "type": "prompt"
        })
        return memories
    
    def add_character(self, character_info):
        """Add a character to the active characters list"""
        character = self.get_character(character_info)
        self.active_characters[character.name] = character
        return character
    
    @property
    def memory_offset(self):
        """Return the memory depth of the character"""
        return self.active_characters_list[0].memory_manager.memory_offset

    @property
    def memory_offset_direction(self):
        """Return the memory offset direction of the character"""
        return self.active_characters_list[0].memory_manager.memory_offset_direction