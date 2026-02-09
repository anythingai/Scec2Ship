from typing import List, Dict
from src.onboarding.models import ChecklistItem, ChecklistState

class OnboardingStorage:
    def __init__(self):
        # Initialize with default checklist items
        self._items: Dict[str, ChecklistItem] = {
            "db_check": ChecklistItem(
                id="db_check",
                title="Database Connection",
                description="Verify database connectivity.",
                is_required=True
            ),
            "api_key_check": ChecklistItem(
                id="api_key_check",
                title="API Key Presence",
                description="Verify API Key configuration.",
                is_required=True
            ),
            "config_check": ChecklistItem(
                id="config_check",
                title="Configuration File",
                description="Verify config file syntax.",
                is_required=True
            )
        }

    def get_items(self) -> List[ChecklistItem]:
        return list(self._items.values())

    def update_item_status(self, item_id: str, is_completed: bool) -> None:
        if item_id in self._items:
            self._items[item_id].is_completed = is_completed

    def get_state(self) -> ChecklistState:
        items = self.get_items()
        total = len(items)
        completed = sum(1 for item in items if item.is_completed)
        percentage = (completed / total * 100.0) if total > 0 else 0.0
