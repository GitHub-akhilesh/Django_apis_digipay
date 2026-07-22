import os
import json
import logging
from typing import Dict, Any
from core.config import settings

logger = logging.getLogger("ai_platform.admin.settings_service")

class SettingsAdminService:
    def __init__(self):
        self.feature_flags = {
            "enableSemanticMemory": True,
            "enableHybridRAG": True,
            "enableStreamingEvents": True,
            "enableTokenAccounting": True,
            "enableHITLConfirmation": True
        }
        # Resolve config storage file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(base_dir, "data")
        self.config_path = os.path.join(self.config_dir, "admin_config.json")
        
        self.load_config()

    def load_config(self):
        """Loads persistent configurations if available."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.feature_flags.update(data.get("featureFlags", {}))
                logger.info(f"Successfully loaded persistent config from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading persistent config: {e}")

    def save_config(self):
        """Saves current configurations to persistent file store."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump({"featureFlags": self.feature_flags}, f, indent=4)
            logger.info(f"Successfully saved config changes to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving persistent config: {e}")

    def get_settings(self) -> Dict[str, Any]:
        """Returns platform system configurations and active feature flags."""
        return {
            "appName": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "featureFlags": self.feature_flags
        }

    def update_feature_flag(self, flag_name: str, enabled: bool) -> Dict[str, Any]:
        """Update platform feature flag online without redeployment."""
        self.feature_flags[flag_name] = enabled
        self.save_config()
        logger.info(f"Admin updated feature flag '{flag_name}' = {enabled}")
        return {
            "flagName": flag_name,
            "enabled": enabled,
            "status": "UPDATED"
        }

settings_admin_service = SettingsAdminService()
