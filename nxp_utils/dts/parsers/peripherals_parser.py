from ..utils import print_xml
from logging import Logger
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pprint import pprint

def parse_peripherals(root=ET.Element, peripheral_types: Dict[str, Any]={}, log=Logger) -> Dict[str, Any]:
    entries = {}
    log.debug("Parsing peripherals")

    # Locate the container node
    node_key = "peripherals"
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
        entry_type = node.get("peripheral_type")
        entry = {
            "id": entry_id,
            "name": node.get("name"),
            "type": entry_type,
            "signals": {}
        }
        if entry_type not in peripheral_types:
            log.error("peripheral type %s for %s not found in peripheral types registry", entry_type, entry_id)
            raise Exception("Malformed peripheral")
        entry["peripheral_spec"] = peripheral_types[entry_type]
        if entry_id in entries:
            log.error("found duplicate peripheral %s in peripherals registry", entry_id)
            raise Exception("Duplicate peripheral")
        # pprint(entry)
        entries[entry_id] = entry

    log.debug("Parsed peripherals", extra={"count": len(entries)})
    # pprint(entries)
    return entries

