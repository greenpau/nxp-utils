def generate_uart_node(peri_id: str, pins: list) -> str:
    """Standard UART template."""
    return f"""
&{peri_id.lower()} {{
    pinctrl-0 = <&{peri_id.lower()}_default>;
    pinctrl-names = "default";
    current-speed = <115200>;
    status = "okay";
}};"""
