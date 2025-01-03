print("Importing simple_thought_process.py")
from src.logging import logging
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from src.thought_processes.branching_thought_process import Question
logging.info("Imported required libraries in simple_thought_process.py")

thought_process_name = "simple"

# Thought Process
class ThoughtProcess(BaseModel):
    """The response format for characters is a schema that requires the assistant to respond in a specific way. The assistant must respond in a way that is consistent with the schema, and must follow the rules of the schema to respond to the user."""
    why_is_the_other_character_saying_this: str = Field(...,description="The question the bot asks themselves to understand why the person they're talking to is saying what they are saying. Should be at least a sentence long.",min_length=1)
    questions: list[Question] = Field(...,min_items=1,max_items=5)
    response_to_user: str = Field(...,description="The final conclusion the character reaches and that is sent to the user as response to their initial query/prompt. Should be at least a paragraph long, but can be much longer as well, and consider everything that the character has thought about. It won't discuss the thought process but will summarize the character's final thoughts. Everything the character has thought about should be considered for inclusion in the conclusion, nothing else will be communicated to the end user.",min_length=1)