print("Importing jungian_thought_process.py")
from src.logging import logging
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from src.thought_processes.branching_thought_process import BranchingThoughts, Question
logging.info("Imported required libraries in jungian_thought_process.py")

thought_process_name = "jungian"

class JungianThought(BaseModel):
    """The characters Jungian response."""
    the_innocent_response: str = Field(...,description="The Innocent response to the user's query. Should be at least a sentence long. The innocent archetype seeks safety and happiness, and desires to be free from harm and wrong-doing.",min_length=1)
    the_orphan_response: str = Field(...,description="The Orphan response to the user's query. Should be at least a sentence long. The orphan archetype seeks connections and belonging, and values being down-to-earth and connecting with others.",min_length=1)
    the_hero_response: str = Field(...,description="The Hero response to the user's query. Should be at least a sentence long. The hero archetype aims to prove worth through courageous acts and difficult challenges, and aspires to use mastery to improve the world.",min_length=1)
    the_caregiver_response: str = Field(...,description="The Caregiver response to the user's query. Should be at least a sentence long. The caregiver archetype aims to help and protect others, often putting others' needs before their own.",min_length=1)
    the_explorer_response: str = Field(...,description="The Explorer response to the user's query. Should be at least a sentence long. The explorer archetype seeks to understand the world and their place in it, and values autonomy, ambition, and being true to oneself.",min_length=1)
    the_rebel_response: str = Field(...,description="The Rebel response to the user's query. Should be at least a sentence long. The rebel archetype seeks radical change and disruption of the status quo, and is willing to destroy what isn't working.",min_length=1)
    the_lover_response: str = Field(...,description="The Lover response to the user's query. Should be at least a sentence long. The lover archetype seeks intimacy and experiences that involve love, relationships, and personal satisfaction.",min_length=1)
    the_creator_response: str = Field(...,description="The Creator response to the user's query. Should be at least a sentence long. The creator archetype aims to create something of enduring value and give form to a vision, and values authenticity and imagination.",min_length=1)
    the_jester_response: str = Field(...,description="The Jester response to the user's query. Should be at least a sentence long. The jester archetype seeks to live in the moment with full enjoyment, and uses humor and play to make others happy.",min_length=1)
    the_sage_response: str = Field(...,description="The Sage response to the user's query. Should be at least a sentence long. The sage archetype seeks truth and understanding, and values wisdom and intelligence.",min_length=1)
    the_magician_response: str = Field(...,description="The Magician response to the user's query. Should be at least a sentence long. The magician archetype aims to make dreams come true and transform reality, and values knowledge and the fundamental laws of how things work.",min_length=1)
    the_ruler_response: str = Field(...,description="The Ruler response to the user's query. Should be at least a sentence long. The ruler archetype seeks control and wants to create a prosperous, successful family or community.",min_length=1)
    shadow_response: str = Field(...,description="The Shadow response to the user's query. Should be at least a sentence long. The shadow is the unconscious part of the personality that contains the repressed weaknesses, desires, and instincts of the individual. The shadow is the dark side of the personality and represents the animal instincts that humans have. It is the part of the personality that is hidden from the outside world.",min_length=1)
    anima_response: str = Field(...,description="The Anima response to the user's query. Should be at least a sentence long. The anima is the feminine side of a character's psyche. It is the part of the personality that is responsible for the emotions and feelings of the individual. The anima is the part of the personality that is responsible for the creative and intuitive side of the individual.",min_length=1)
    animus_response: str = Field(...,description="The Animus response to the user's query. Should be at least a sentence long. The animus is the masculine side of a character's psyche. It is the part of the personality that is responsible for the logical and rational side of the individual. The animus is the part of the personality that is responsible for the intellectual and analytical side of the individual.",min_length=1)
    self_response: str = Field(...,description="The Self response to the user's query. Should be at least a sentence long. The self is the center of the personality and is the part of the personality that is responsible for the integration of the conscious and unconscious aspects of the individual. The self is the part of the personality that is responsible for the development of the individual's personality.",min_length=1)

class ThoughtProcess(BaseModel):
    """The response format for characters is a schema that requires the AI to respond in a specific way. The AI must respond in a way that is consistent with the schema, and must follow the rules of the schema to solve the user's queries."""
    jungian_thought: JungianThought
    thought_branches: list[BranchingThoughts] = Field(...,min_items=1,max_items=5)
    questions: list[Question] = Field(...,min_items=1,max_items=5)
    response_to_user: str = Field(...,description="The final conclusion the character reaches and that is sent to the user as response to their initial query/prompt. Should be at least a paragraph long, but can be much longer as well, and consider everything that the character has thought about. It won't discuss the thought process, or directly reference the Jungian responses, but will summarize the character's final thoughts. Everything the character has thought about should be considered for inclusion in the conclusion, nothing else will be communicated to the end user.",min_length=1)