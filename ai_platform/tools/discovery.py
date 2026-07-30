import os
import importlib
import logging
from tools.decorator import REGISTERED_TOOLS

logger = logging.getLogger("ai_platform.tools.discovery")

# Infrastructure modules inside tools/ that define no tools. `catalog` and
# `registry` both read TOOL_REGISTRY, so importing them mid-discovery would be a
# circular import.
SKIP_MODULES = {"decorator.py", "discovery.py", "registry.py", "catalog.py"}


def discover_tools():
    """Dynamically scan and import all modules inside tools/ directory."""
    tools_dir = os.path.dirname(os.path.abspath(__file__))

    for root, dirs, files in os.walk(tools_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if not file.endswith(".py") or file.startswith("__") or file in SKIP_MODULES:
                continue

            # Build the dotted module path. splitext is required here: stripping
            # ".py" with str.rstrip removes ANY trailing '.', 'p' or 'y', which
            # silently turned tools/aeps/balance_enquiry.py into
            # "tools.aeps.balance_enquir" and tools/settlement/payout.py into
            # "tools.settlement.payou" — so those tools never registered.
            rel_path = os.path.relpath(os.path.join(root, file), tools_dir)
            module_path = os.path.splitext(rel_path)[0].replace(os.sep, ".")
            module_name = f"tools.{module_path}"

            try:
                importlib.import_module(module_name)
                logger.debug(f"Auto-discovered tool module: {module_name}")
            except Exception as e:
                logger.warning(f"Failed to auto-discover module {module_name}: {e}")

    logger.info(f"Auto-discovery complete. Discovered {len(REGISTERED_TOOLS)} tools.")
    return REGISTERED_TOOLS
