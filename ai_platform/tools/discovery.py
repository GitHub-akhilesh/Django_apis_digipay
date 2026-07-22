import os
import pkgutil
import importlib
import logging
from tools.decorator import REGISTERED_TOOLS

logger = logging.getLogger("ai_platform.tools.discovery")

def discover_tools():
    """Dynamically scan and import all modules inside tools/ directory."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    
    for root, dirs, files in os.walk(tools_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__") and file not in ["decorator.py", "discovery.py", "registry.py"]:
                # Construct Python import module path
                rel_path = os.path.relpath(os.path.join(root, file), tools_dir)
                module_name = "tools." + rel_path.replace(os.sep, ".").rstrip(".py")
                try:
                    importlib.import_module(module_name)
                    logger.debug(f"Auto-discovered tool module: {module_name}")
                except Exception as e:
                    logger.warning(f"Failed to auto-discover module {module_name}: {e}")

    logger.info(f"Auto-discovery complete. Discovered {len(REGISTERED_TOOLS)} tools.")
    return REGISTERED_TOOLS
