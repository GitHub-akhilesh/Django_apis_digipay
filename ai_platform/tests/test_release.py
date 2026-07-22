import os
import pytest
from admin.settings_service import settings_admin_service

def test_settings_persistence(tmp_path):
    # Temporarily override config path to use tmp_path
    original_path = settings_admin_service.config_path
    original_dir = settings_admin_service.config_dir
    
    settings_admin_service.config_dir = str(tmp_path)
    settings_admin_service.config_path = os.path.join(str(tmp_path), "admin_config.json")
    
    try:
        # Update flag
        settings_admin_service.update_feature_flag("enableSemanticMemory", False)
        
        # Verify file is created and contains flag value
        assert os.path.exists(settings_admin_service.config_path)
        
        # Instantiate a new service to verify it loads from file
        from admin.settings_service import SettingsAdminService
        new_service = SettingsAdminService()
        # Direct path copy for new instance
        new_service.config_dir = str(tmp_path)
        new_service.config_path = os.path.join(str(tmp_path), "admin_config.json")
        new_service.load_config()
        
        assert new_service.feature_flags["enableSemanticMemory"] is False
    finally:
        # Restore original paths
        settings_admin_service.config_dir = original_dir
        settings_admin_service.config_path = original_path

def test_release_documentation_presence():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    docs_dir = os.path.join(base_dir, "docs")
    
    required_docs = [
        "architecture.md",
        "deployment.md",
        "api_reference.md",
        "developer_guide.md",
        "operator_guide.md",
        "troubleshooting.md",
        "disaster_recovery.md"
    ]
    
    for doc in required_docs:
        doc_path = os.path.join(docs_dir, doc)
        assert os.path.exists(doc_path), f"Required documentation file {doc} is missing"
        with open(doc_path, "r") as f:
            content = f.read()
            assert len(content) > 100, f"Documentation file {doc} seems empty or too short"
