"""
Configuration API endpoints.
"""
from fastapi import APIRouter, HTTPException
import json
import os
from typing import Dict, Any

from api.models import ConfigResponse, ConfigUpdateRequest, ConfigUpdateResponse

router = APIRouter()

CONFIG_FILE = "config.json"


def mask_token(token: str) -> str:
    """Mask sensitive token, showing only last 4 characters."""
    if not token or len(token) <= 4:
        return "****"
    return "*" * (len(token) - 4) + token[-4:]


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """
    Get current configuration (with masked sensitive values).
    
    Returns:
        Configuration data with masked tokens
    """
    try:
        # Load config file
        if not os.path.exists(CONFIG_FILE):
            raise HTTPException(status_code=404, detail="Configuration file not found")
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Get Apify token
        apify_token = config.get("apify_token", "")
        
        # Check which platforms have auth configured
        has_auth = {}
        for platform in ["upwork", "fiverr", "freelancer", "peopleperhour"]:
            platform_config = config.get(f"{platform}_auth", {})
            has_auth[platform] = bool(
                platform_config.get("username") and platform_config.get("password")
            )
        
        return ConfigResponse(
            apify_token=mask_token(apify_token),
            platforms=["Upwork", "Fiverr", "Freelancer", "PeoplePerHour"],
            has_auth=has_auth
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load configuration: {str(e)}")


@router.post("/", response_model=ConfigUpdateResponse)
async def update_config(request: ConfigUpdateRequest):
    """
    Update configuration.
    
    Request Body:
        ConfigUpdateRequest with optional fields to update
    
    Returns:
        Success status and message
    """
    try:
        # Load existing config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Update Apify token if provided
        if request.apify_token:
            config["apify_token"] = request.apify_token
        
        # Update platform auth if provided
        if request.platform_auth:
            for platform, credentials in request.platform_auth.items():
                if platform in ["upwork", "fiverr", "freelancer", "peopleperhour"]:
                    config[f"{platform}_auth"] = credentials
        
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        
        return ConfigUpdateResponse(
            status="success",
            message="Configuration updated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")
