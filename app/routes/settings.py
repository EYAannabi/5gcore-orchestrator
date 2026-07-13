"""
Settings management routes.
Handles persistent application settings storage and retrieval.
"""

import logging
import json
import os
from fastapi import APIRouter, HTTPException
from app.models.deployment import SettingsModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Configuration"])

# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "../", "settings.json")


def _load_settings() -> SettingsModel:
    """Load settings from file or return defaults"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                return SettingsModel(**data)
    except Exception as e:
        logger.warning(f"Error loading settings: {e}")
    
    return SettingsModel()


def _save_settings(settings: SettingsModel) -> bool:
    """Save settings to file"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings.dict(), f, indent=2)
        logger.info("Settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


@router.get("", response_model=SettingsModel)
async def get_settings():
    """
    Retrieve current application settings.
    
    Returns all configurable settings including namespace, helm paths,
    refresh intervals, and UI preferences.
    
    Returns:
        SettingsModel with current settings
    """
    try:
        settings = _load_settings()
        logger.info("Retrieved settings")
        return settings
    except Exception as e:
        logger.error(f"Error retrieving settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving settings: {str(e)}")


@router.post("", response_model=SettingsModel)
async def update_settings(settings: SettingsModel):
    """
    Update application settings.
    
    Validates and persists new settings. All settings are validated
    through Pydantic before storage.
    
    Args:
        settings: New settings object
        
    Returns:
        Updated SettingsModel
    """
    try:
        if _save_settings(settings):
            logger.info("Settings updated successfully")
            return settings
        else:
            raise HTTPException(status_code=500, detail="Failed to save settings")
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid settings: {str(e)}")


@router.post("/reset")
async def reset_settings():
    """
    Reset settings to defaults.
    
    Removes the settings file and returns to default configuration.
    
    Returns:
        Default SettingsModel
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
            logger.info("Settings reset to defaults")
        
        return _load_settings()
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=f"Error resetting settings: {str(e)}")
