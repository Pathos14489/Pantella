print("Importing freudian_thought_process.py")
from src.logging import logging
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from src.thought_processes.branching_thought_process import BranchingThoughts, Question
logging.info("Imported required libraries in freudian_thought_process.py")

thought_process_name = "freudian"

class FreudianThought(BaseModel):
    """The character's Freudian response. Should take into account the three different parts of the mind and respond for each one."""
    id_response: str = Field(...,description="The ID response to the user's query. Should be at least a sentence long. The id is the division of the psyche that is completely unconscious. This is where the drives and needs of a person come from. They are driven by instinct, and the psychic energy comes from here. Since it deals with basic instincts, Freud assumed the id is part of the unconscious due to the principles of pleasure, satisfaction, and gratification.",min_length=1)
    ego_response: str = Field(...,description="The Ego response to the user's query. Should be at least a sentence long. The ego is the self as contrasted by another self. Once the ego has developed, it is responsible for mediating between the unrealistic id and the reality. It uses reality to help the id satisfy its demands and to obtain what the ego seeks. Much like the id, the ego seeks out pleasure by reducing tension that has been created and avoids pain.",min_length=1)
    super_ego_response: str = Field(...,description="The Super Ego response to the user's query. Should be at least a sentence long. The superego is part of the psyche that is partly conscious. It represents the rules of society, functions to reward and punish through a system of moral attitudes, and has a sense of guilt. The development for the superego happens around ages 3 to 5. Its function is to control the impulses of the id by using the rules of society, what is forbidden and what is allowed.",min_length=1)

class ThoughtProcess(BaseModel):
    """The response format for characters is a schema that requires the AI to respond in a specific way. The AI must respond in a way that is consistent with the schema, and must follow the rules of the schema to solve the user's queries."""
    freudian_thought: FreudianThought
    thought_branches: list[BranchingThoughts] = Field(...,min_items=1,max_items=5)
    questions: list[Question] = Field(...,min_items=1,max_items=5)
    response_to_user: str = Field(...,description="The final conclusion the character reaches and that is sent to the user as response to their initial query/prompt. Should be at least a paragraph long, but can be much longer as well, and consider everything that the character has thought about. It won't discuss the thought process, or directly reference the Id, Ego or Super Ego, but will summarize the character's final thoughts. Everything the character has thought about should be considered for inclusion in the conclusion, nothing else will be communicated to the end user.",min_length=1)