import re
from typing import List, Dict, Any, Tuple
from .pin_entry import PinEntry

def generate_pinctrl_entry(node_name: str, pins: List[PinEntry]) -> str:
    """
    Generates a pinctrl node string with sub-grouping for differing electrical properties.
    """
    dts: List[str] = [f"    {node_name.lower()}: {node_name.lower()} {{"]

    # Signature: (pull, drive_strength, slew_rate, open_drain, passive_filter)
    sub_groups: Dict[Tuple[Any, ...], List[PinEntry]] = {}

    for p in pins:
        config_sig = (p.pull, p.drive_strength, p.slew_rate, p.open_drain, p.passive_filter, p.digital_filter)

        if config_sig not in sub_groups:
            sub_groups[config_sig] = []
        sub_groups[config_sig].append(p)

    for i, (config, group_pins) in enumerate(sub_groups.items(), 1):
        pull, drive, slew, od, p_filter, d_filter = config

        dts.append(f"        group{i} {{")
        dts.append("            pinmux = <")

        for j, p in enumerate(group_pins):
            comma = "," if j < len(group_pins) - 1 else ""

            # Use regex to extract Port and Pin Index
            match = re.match(r"PT([A-E])(\d+)", p.base_pin)
            if not match:
                continue

            port, idx = match.groups()
            label = p.user_label or p.func_label or p.base_pin

            dts.append(f"                K64_PSEL({port}, {idx}, {p.mux_value}){comma} /* {label} */")

        dts.append("            >;")

        # Property translation to DTS strings
        if pull in ['up', 'down']:
            dts.append(f"            bias-pull-{pull};")
        if drive:
            dts.append(f"            drive-strength = \"{drive}\";")
        if slew:
            dts.append(f"            slew-rate = \"{slew}\";")
        if od in [True, 'enable']:
            dts.append("            drive-open-drain;")
        if p_filter in [True, 'enable']:
            dts.append("            passive-filter;")
        if d_filter in [True, 'enable']:
            dts.append("            digital-filter;")
        dts.append("        };")

    dts.append("    };")
    return "\n".join(dts)
