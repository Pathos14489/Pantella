from src.behavior_managers.base_behavior_manager import base_BehaviorManager
from src.logging import logging

valid_games = ["fallout4","skyrim","fallout4vr","skyrimvr"]
manager_slug = "default_behavior_manager"

class BehaviorManager(base_BehaviorManager):
    def __init__(self,conversation_manager):
        super().__init__(conversation_manager)
        logging.info("Loading default behavior manager")