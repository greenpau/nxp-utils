from ..utils import print_xml
from logging import Logger
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
from pprint import pprint


def _parse_channels(signal_node: ET.Element) -> List[Dict[str, str]]:
    """Extracts channel information if present (common in ADC/DMA)."""
    channels = []
    for chan in signal_node.findall('.//signal_channel'):
        channels.append({
            "id": chan.get("id"),
            "name": chan.get("name"),
            "directions": chan.get("directions"),
            "modes": chan.get("modes")
        })
    return channels

def parse_peripheral_types(root=ET.Element, log=Logger) -> Dict[str, Any]:
    entries = {}
    log.debug("Parsing peripheral types")

    # Locate the container node
    node_key = "peripheral_types"
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
            "signals": {}
        }

        for sig in node.findall('.//peripheral_signal'):
            sig_id = sig.get('id')
            sig_data = {
                "unified_ids": sig.get("unified_ids"),
                "directions": sig.get("directions"),
                "modes": sig.get("modes"),
                "channels": _parse_channels(sig),
                "features": [f.get("id") for f in sig.findall('.//signal_feature')]
            }
            entry["signals"][sig_id] = sig_data
        # pprint(entry)
        entries[entry_id] = entry
    log.debug("Parsed peripheral types", extra={"count": len(entries)})
    # pprint(entries)
    return entries

