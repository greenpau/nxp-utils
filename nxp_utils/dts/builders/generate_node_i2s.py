def generate_i2s_node(peri_id: str, pins: list) -> str:
    """Templates for 16kHz, 16-bit PCM Audio."""
    return f"""
&{peri_id.lower()} {{
    pinctrl-0 = <&{peri_id.lower()}_default>;
    pinctrl-names = "default";
    status = "okay";

    /* Audio Format Configuration */
    protocol = "i2s";
    bit-format = "s16le";      /* Signed 16-bit Little Endian */
    sample-rate = <16000>;     /* 16 kHz */

    /* INMP441 Specifics */
    receiver {{
        /* Sync RX to the TX clocks we defined on PTB18/19 */
        sync-mode = <1>; 
        data-lane = <0>;
    }};
}};"""
