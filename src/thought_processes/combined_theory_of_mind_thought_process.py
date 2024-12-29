print("Importing combined_theory_of_mind_thought_process.py")
from src.logging import logging
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from src.thought_processes.base_thought_process import BranchingThoughts, Question
from src.thought_processes.jungian_thought_process import JungianThought
from src.thought_processes.freudian_thought_process import FreudianThought
logging.info("Imported required libraries in combined_theory_of_mind_thought_process.py")

thought_process_name = "combined_theory_of_mind"

class ThoughtProcess(BaseModel):
    """The response format for characters is a schema that requires the AI to respond in a specific way. The AI must respond in a way that is consistent with the schema, and must follow the rules of the schema to solve the user's queries."""
    freudian_thought: FreudianThought
    jungian_thought: JungianThought
    thought_branches: list[BranchingThoughts] = Field(...,min_items=1,max_items=5)
    questions: list[Question] = Field(...,min_items=1,max_items=5)
    response_to_user: str = Field(...,description="The final conclusion the character reaches and that is sent to the user as response to their initial query/prompt. Should be at least a paragraph long, but can be much longer as well, and consider everything that the character has thought about. It won't discuss the thought process, or directly reference the Id, Ego, Super Ego, or any of the Jungian parts, but will summarize the character's final thoughts. Everything the character has thought about should be considered for inclusion in the conclusion, nothing else will be communicated to the end user.",min_length=1)