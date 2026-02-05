import re
from typing import List, Dict
from .pin_entry import PinEntry

INTERRUPT_MAP = {
    'kPORT_InterruptRisingEdge': 'GPIO_INT_EDGE_RISING',
    'kPORT_InterruptFallingEdge': 'GPIO_INT_EDGE_FALLING',
    'kPORT_InterruptEitherEdge': 'GPIO_INT_EDGE_BOTH',
    'kPORT_InterruptLogicZero': 'GPIO_INT_LEVEL_LOW',
    'kPORT_InterruptLogicOne': 'GPIO_INT_LEVEL_HIGH',
}

def generate_gpio_logic_nodes(pins: List[PinEntry]) -> str:
    """
    Generates high-level GPIO nodes for LEDs, Buttons, or general 
    GPIO configuration based on init states and interrupts.
    """
    output = []
    
    # Sort pins by port for clean grouping (gpioa, gpiob, etc.)
    port_groups: Dict[str, List[PinEntry]] = {}
    
    for p in pins:
        # We only care about GPIO signals here
        if "GPIO" not in p.func_label:
            continue

        # Ensure base_pin access is consistent
        match = re.match(r"PT([A-E])(\d+)", p.base_pin)
        if not match: 
            continue

        port_letter = match.group(1).lower()
        
        if port_letter not in port_groups:
            port_groups[port_letter] = []
        port_groups[port_letter].append(p)

    for port, group_pins in sorted(port_groups.items()):
        output.append(f"&gpio{port} {{")
        output.append("    status = \"okay\";")
        
        for p in group_pins:
            match = re.match(r"PT([A-E])(\d+)", p.base_pin)
            idx = match.group(2)
            
            # Determine Flags
            flags = []
            if p.pull == "up": flags.append("GPIO_PULL_UP")
            elif p.pull == "down": flags.append("GPIO_PULL_DOWN")
            
            # Add Interrupt Logic
            if p.gpio_interrupt and p.gpio_interrupt in INTERRUPT_MAP:
                flags.append(INTERRUPT_MAP[p.gpio_interrupt])
            
            # Default to active high if not specified
            active_logic = "GPIO_ACTIVE_LOW" if p.gpio_init_state is False else "GPIO_ACTIVE_HIGH"
            flags.append(active_logic)
            
            flag_str = " | ".join(flags) if flags else "0"
            node_name = (p.user_label or f"pin_{idx}").lower().replace(" ", "_")
            
            output.append(f"    {node_name} {{")
            output.append(f"        gpios = <&gpio{port} {idx} ({flag_str})>;")
            
            # Add Init State (logical)
            if p.gpio_init_state is not None:
                state_str = "high" if p.gpio_init_state else "low"
                output.append(f"        output-{state_str};")
                
            output.append("    };")
            
        output.append("};\n")
        
    return "\n".join(output)