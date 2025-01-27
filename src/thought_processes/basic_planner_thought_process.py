print("Importing basic_planner_thought_process.py")
from src.logging import logging
from pydantic import BaseModel, Field
from src.thought_processes.branching_thought_process import BranchingThoughts, Question
logging.info("Imported required libraries in basic_planner_thought_process.py")

thought_process_name = "basic_planner"

class ThoughtProcess(BaseModel):
    """The response format for characters is a schema that requires the assistant to respond in a specific way. The assistant must respond in a way that is consistent with the schema, and must follow the rules of the schema to respond to the user."""
    why_is_the_user_saying_this: Question = Field(...,description="The question the character asks themselves to understand why the user is saying what they are saying. Should be at least a sentence long.",min_length=1)
    thought_branches: list[BranchingThoughts] = Field(...,min_items=1,max_items=5)
    questions: list[Question] = Field(...,min_items=1,max_items=5)
    plan: list[str] = Field(...,description="The plan the character makes to figure out how to respond to the user. Should be at least step item long and less than six steps total. Each step should be anywhere from a sentence to a paragraph in length.",min_items=1,max_items=5)
    response_to_user: str = Field(...,description="The final conclusion the character reaches and that is sent to the user as response to their initial query/prompt. Should be at least a paragraph long, but can be much longer as well, and consider everything that the character has thought about. It won't discuss the thought process but will summarize the character's final thoughts. Everything the character has thought about should be considered for inclusion in the conclusion, nothing else will be communicated to the end user.",min_length=1)