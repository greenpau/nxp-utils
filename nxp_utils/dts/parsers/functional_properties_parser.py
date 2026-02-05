from ..utils import print_xml
from logging import Logger
import xml.etree.ElementTree as ET
from typing import Dict, Any
from pprint import pprint

def parse_functional_properties(root=ET.Element, log=Logger) -> Dict[str, Any]:
    entries = {}
    log.debug("Parsing functional properties")

    # Locate the container node
    node_key = "functional_properties_declarations"
    declarations_node = root.find(node_key)
    if declarations_node is None:
        log.warning("No %s found in XML", node_key)
        return entries

    nodes = root.find(node_key)
    for node in nodes:
        # print('\n')
        # print_xml(node)
        entry_id = node.get("id")
        if not entry_id:
            continue
        entry = {
            "id": entry_id,
            "name": node.get("name"),
            "description": node.get("description"),
            "applicable_modes": [],
            "states": {}
        }

        # Parse Applicable Modes (Directions: in/out/inOut)
        for mode in node.findall(".//applicable_mode"):
            direction = mode.get("directions")
            if direction:
                entry["applicable_modes"].append(direction)

        # Parse State Declarations (The actual hardware values/enums)
        for state in node.findall("state_declaration"):
            state_id = state.get("id")
            if state_id:
                entry["states"][state_id] = {
                    "name": state.get("name"),
                    "description": state.get("description")
                }
        # pprint(entry)
        entries[entry_id] = entry
    log.debug("Parsed functional properties", extra={"count": len(entries)})
    # pprint(entries)
    return entries