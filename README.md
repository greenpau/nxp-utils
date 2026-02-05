# nxp-utils

NXP Microcontroller Utilities library for K64F.

NOTE: If you ever want to chat about robotics, AI, and 3D, please reach out!

<!-- begin-markdown-toc -->
## Table of Contents

* [Getting Started](#getting-started)
* [Generator](#generator)
  * [Signal Configuration](#signal-configuration)
    * [Processing Logic](#processing-logic)
    * [Generating DTS](#generating-dts)
  * [User Selection](#user-selection)
* [Manual Generation](#manual-generation)
  * [Base Register Addresses (PORT Modules)](#base-register-addresses-port-modules)
  * [Manual User Preferences](#manual-user-preferences)
  * [The Mapping Logic](#the-mapping-logic)
  * [Sample Pinctrl Result for K64F](#sample-pinctrl-result-for-k64f)

<!-- end-markdown-toc -->

## Getting Started

Download `ConfigToolsData` file for your board.

```bash
unzip -d downloads/ConfigToolsData_FRDM-K64F_v25_12 downloads/ConfigToolsData_FRDM-K64F_v25_12.zip
```

### Build DTS

Next, generate `.dts` file:

```bash
dtsbuilder --build-dts \
--input-config-tools-data-file downloads/ConfigToolsData_FRDM-K64F_v25_12.zip \
--user-board-config-file config/board_config.yaml \
--output-dts-path tmp/frdm_k64f-pinctrl.dtsi
```

### Query

```bash
dtsbuilder --query-dts \
--input-config-tools-data-file downloads/ConfigToolsData_FRDM-K64F_v25_12.zip \
--find-base-pin PTC15
```


## Generator

### Signal Configuration

#### Processing Logic

When the builder runs, it retrieves files for the processor:

```text
downloads/ConfigToolsData_FRDM-K64F_v25_09/processors/MK64FN1M0xxx12/ksdk2_0/MK64FN1M0VLL12
├── DMA.js
├── module_clocks.xml
├── part_info.xml
├── peripherals_model_info.xml
├── registers
│   ├── DMAMUX.xml
│   ├── PORTA.xml
│   ├── PORTB.xml
│   ├── PORTC.xml
│   ├── PORTD.xml
│   └── registers.xml
├── resource_tables
│   ├── dmaMuxRequests.xml
│   └── interrupts.xml
└── signal_configuration.xml
```

The essence of `dtsbuilder` script is to parse a **Hardware Pin-to-Signal Mapping Table**, which
describes exactly how a single physical piece of silicon (in this case, pin `C10`) can be "morphed"
into different functional roles. Then, it constructs `.dtsi` file.

```xml
    <pin
        name="ADC1_SE4a/PTE0/SPI1_PCS1/UART1_TX/SDHC0_D1/TRACE_CLKOUT/I2C1_SDA/RTC_CLKOUT"
        description="ADC1 analog channel 4;General purpose IO, Port E, bit 0;SPI1 Peripheral Chip Select 1;Transmit data;D1 - Data 1;Trace clock output;I2C1 Serial Data Line;Oscillator output"
        coords="C10">
```

In the NXP world, this is the "Truth Map" that tells us which `MUX` value corresponds to which peripheral function.

Key Components of the Pin Map:

* **Pin Identification**: Physical Pin **C10**, known as `PTE0` (Port E, Bit 0).
* **The Multiplexer (ALT modes)**: The `<connections>` tags define the available "Personalities" for this pin:
  - **ALT 0**: ADC1 (Analog input)
  - **ALT 1**: GPIO (General Purpose I/O)
  - **ALT 3**: UART1 TX (Serial Transmit)
  - **ALT 6**: I2C1 SDA (Data line)
* **The Configuration Logic**: Inside each connection, the `<assign>` tag tells us the register value
  needed. *For example,* to make this pin a UART1 TX, we must set `PORTE_PCR0[MUX]` to `0x3`.
* **Electrical Defaults**: The `<functional_properties>` section defines the hardware-supported "tweaks"
  like `pull_enable`, `slew_rate`, and `drive_strength`.

In a Linux or Zephyr Device Tree, a `pinctrl` node needs to know two things: **Which pin?**
and **What MUX value?** This XML provides both.

If we were writing a `pinctrl` node for **UART1**, we would look at the `UART1_TX` section of the XML:

```dts
/* Generated logic from the XML */
uart1_default: uart1_default {
    group1 {
        psels = <NX_PSEL(UART1_TX, E, 0)>; /* Port E, Pin 0 */
        drive-strength = "low";           /* From <functional_property id="drive_strength"> */
        bias-pull-down;                   /* From <functional_property id="pull_select"> */
    };
};
```

To generate a `pinctrl` file, `dtsbuilder` script processes this XML as follows:

* **Extract the Pin Mux Value**: Look for the `bit_field_value` where `bit_field="MUX"`. For UART1_TX on PTE0, this value is `0x3`.
* **Map Functions to Peripherals**: Create a lookup table where `Peripheral=UART1` and `Signal=TX` points to `Pin=PTE0, Mux=3`.
* **Handle Electrical Flags**:
   - If `<functional_property id="pull_enable">` is "enable" and `<pull_select>` is "up", add `bias-pull-up` to the DTS.
   - If `<slew_rate>` is "fast", add `slew-rate = <0>`.
* **Detect Conflicts**: Use the `<disallow>` tags in the XML to warn the user if they try to use
  the same internal signal (like `SPI1_PCS1`) on two different physical pins simultaneously.

First, the parser reads `pins`.

```py
['ADC1_SE4a', 'PTE0', 'SPI1_PCS1', 'UART1_TX', 'SDHC0_D1', 'TRACE_CLKOUT', 'I2C1_SDA', 'RTC_CLKOUT']
['ADC1_SE5a', 'PTE1', 'LLWU_P0', 'SPI1_SOUT', 'UART1_RX', 'SDHC0_D0', 'TRACE_D3', 'I2C1_SCL', 'SPI1_SIN']
['ADC0_DP2', 'ADC1_SE6a', 'PTE2', 'LLWU_P1', 'SPI1_SCK', 'UART1_CTS_b', 'SDHC0_DCLK', 'TRACE_D2']
['ADC0_DM2', 'ADC1_SE7a', 'PTE3', 'SPI1_SIN', 'UART1_RTS_b', 'SDHC0_CMD', 'TRACE_D1', 'SPI1_SOUT']
```

These lists represent the **mux groups** for every pin on the MCU. Each list is essentially a single
physical "pad" on the chip, and the strings inside are the different functional "labels" that pad can assume.

From a parser's perspective, this is the **Pin Master List**.

Not all of these will go into a `pinctrl` file in the same way. We need to categorize them:

* **Multiplexed Pins (The majority):** e.g., `['PTA1', 'UART0_RX', ...]`
  - These are the primary targets for `pinctrl`.
  - One label is always the "GPIO" name (starts with `PT`).
* **Dedicated Power/Ground:** e.g., `['VDD63']`, `['VSS64']`
  - Ignore these for `pinctrl`. They have no MUX configuration.
* **Analog/Dedicated Inputs:** e.g., `['USB0_DP']`, `['RESET_b']`
  - Usually "Fixed Function." We rarely need a `pinctrl` entry for these unless the SoC
    requires an "Analog Mode" mux setting.

To handle these lists effectively, the parser should follow these rules:

**Rule A**: Find the "Key" (The GPIO Name)

In the Kinetis/NXP ecosystem, the `PTxN` label is the hardware "anchor."

* **Input:** `['PTA2', 'UART0_TX', 'FTM0_CH7', 'JTAG_TDO', 'TRACE_SWO', 'EZP_DO']`
* **Logic:** `base = "PTA2"`. From this, we know it belongs to **Port A** at **Index 2**.
* **Register Calculation:** This tells us to modify the `PORTA_PCR2` register.

**Rule B**: Map Function to ALT Mode.

The index of the label in the list often corresponds directly to the `ALT` number in the hardware.

* `ALT0`: `PTA2` (Standard for some, though usually ALT1 is GPIO)
* `ALT1`: `UART0_TX`
* `ALT2`: `FTM0_CH7`
* ...and so on.

*Note: The XML's `<connections package_function="alt3">` is the ultimate source of truth for which index matches which ALT mode.*

**Rule C**: Handling "Special" Pins

We have several entries that look like this:

```text
['ADC0_DP0', 'ADC1_DP3']
['VREF_OUT', 'CMP1_IN5', 'CMP0_IN5', 'ADC1_SE18']
```

These are **Analog-only pins**. They don't have a `PTx` label, meaning they cannot be used as General Purpose I/O.
We don't usually create `pinctrl` nodes for these because they don't have a Mux register to configure. The
hardware connects them to the ADC/Comparator by default.

#### Generating DTS

For example, get only pins that actually need a MUX configuration for UART1

```py
routable_uart_tx = [p for p in mapping["UART1"]["TX"] if p["is_routable"]]
```

It `routable_uart_tx` follows:

```py
[{'alt_mode': 'alt3',
  'base_pin': 'PTE0',
  'coords': '1',
  'description': 'Transmit data',
  'func_label': 'UART1_TX',
  'is_routable': True,
  'mux_value': '0x3'},
 {'alt_mode': 'alt3',
  'base_pin': 'PTC4',
  'coords': '76',
  'description': 'Transmit data',
  'func_label': 'UART1_TX',
  'is_routable': True,
  'mux_value': '0x3'}]
```

This output means that for the **UART1_TX** signal, the MCU has **two physical pin options**. We can
choose to route the UART transmitter to either **PTE0** (Pin 1) or **PTC4** (Pin 76).

This is a classic "Pin Multiplexing" scenario. Since a single peripheral signal can only be used in
one place at a time, we have to decide which physical pin works best for our PCB layout.

| Field         | Meaning                                                                                                         |
| ------------- | --------------------------------------------------------------------------------------------------------------- |
| `base_pin`    | The GPIO name. This tells us which Port (E or C) and Pin (0 or 4) to look for.                                  |
| `coords`      | The physical pin number (package lead/ball). Pin **1** vs Pin **76**.                                           |
| `mux_value`   | The value we must write into the Pin Control Register (PCR) to "activate" this function. Both use `0x3` (ALT3). |
| `is_routable` | `True` confirms these are standard pins with MUX registers (not fixed-function power/analog pins).              |

In a Device Tree, we generally define "Pin Groups." Because there are two options, we typically look at the
hardware schematic or custom `.mex` configuration to see which one is actually wired up.

If we chose `PTE0`, the DTS entry would look like this (standard NXP/Zephyr format):

```c
uart1_tx_default: uart1_tx_default {
    /* Muxing UART1_TX to Port E Pin 0 with Alt Mode 3 */
    nxp,psels = <NX_PSEL(UART1_TX, E, 0, 0x3)>;
};
```

If we chose `PTC4`, then 

```c
uart1_tx_default: uart1_tx_default {
    /* Muxing UART1_TX to Port C Pin 4 with Alt Mode 3 */
    nxp,psels = <NX_PSEL(UART1_TX, C, 4, 0x3)>;
};
```

### User Selection

To build a production-ready `pinctrl` (Pin Control) file for a Device Tree (DTS/DTSI), parsing
the `signal_configuration.xml` is mandatory. To finish the job, we need to gather three
additional "ingredients" to ensure the generated code is hardware-accurate and matches the user's
specific board design. The `signal_configuration.xml` tells us what is **possible** (e.g., UART1_TX
can be on PTE0 *or* PTC4). We need the user's configuration file to know what is **chosen**.

Download [MCUXpresso Config Tools, mac OS AARCH package](https://www.nxp.com/design/design-center/software/development-software/mcuxpresso-software-and-tools-/mcuxpresso-config-tools-pins-clocks-and-peripherals:MCUXpresso-Config-Tools).

However, the tool does not work for `FRDM-K64F`.

We can provide selection in `pins.xml`.

* **What to look for:** Look for the `<pins>` or `<hardware>` tags in the user's project file.
* **Why:** It contains the "Selection" (e.g., "For this project, use PTC4 for UART1_TX").
* **Result:** This filters our list of options down to a single physical mapping.

A `pinctrl` node isn't just about the Mux; it's about the electrical characteristics of the
pad. Without this, our UART might not have enough "drive" to send data, or our I2C might
fail because the pull-up resistors aren't enabled.

We need to map the parsed `functional_properties` to DTS properties:

* `pull_select="up"`  `bias-pull-up;`
* `drive_strength="high"`  `drive-strength = "high";`
* `slew_rate="slow"`  `slew-rate = <1>;`
* `passive_filter="enable"`  `nxp,passive-filter;`

Next, register base addresses and offsets. The Device Tree needs to know where
the **PORT** and **GPIO** modules live in the memory map.

* **The Problem:** The XML says "Port E, Pin 0". The hardware needs to know that Port E starts at `0x4004D000`.
* **The Source:** This is usually found in a `memory_map.xml` or `processor.xml` within the NXP data pack.
* **The Math:** *(e.g., PORTE_PCR0 is at Base + 0, PCR1 is at Base + 4, etc.)*

Most NXP Device Trees (especially in Zephyr) use a macro to compress the
data (e.g. `PSEL` logic). We need to verify which macro format our specific SoC uses.

Common Format are:

`nxp,psels = <NX_PSEL(SIGNAL, PORT, PIN, MUX)>;`

To generate this, you need a helper function to convert:

* `"PTE0"`  `E, 0`
* `"PTC4"`  `C, 4`

## Manual Generation

The **FRDM-K64F** is a legendary development board, but NXP's modern Config Tools (v15/v16) have
started deprecating support for older Kinetis "K" series parts in favor of MCUXpresso and
newer i.MX/LPC silicon.

We need to recreate the **Pin Routing Engine**. To get the `pinctrl` file for a K64F without the
official GUI, we need to synthesize three things.

### Base Register Addresses (PORT Modules)

The K64F has five ports: **PORTA** through **PORTE**. In our `pinctrl` file, we need the
base addresses to calculate where the MUX configuration actually goes.

| Port    | Base Address | Register Type              |
| ------- | ------------ | -------------------------- |
| `PORTA` | `0x40049000` | PCR (Pin Control Register) |
| `PORTB` | `0x4004A000` | PCR                        |
| `PORTC` | `0x4004B000` | PCR                        |
| `PORTD` | `0x4004C000` | PCR                        |
| `PORTE` | `0x4004D000` | PCR                        |

**The Formula:**

Since you've already parsed the pin index (like `0` from `PTE0`), the memory location for the mux is:

*Example: `PTE0` MUX is at `0x4004D000`. `PTE1` is at `0x4004D004`.*

### Manual User Preferences

Since the Config Tools won't give us a `pins.xml` for the K64F, we'll have to create
a simplified version based on the **FRDM-K64F Schematic**.

For example, on the FRDM-K64F, the **Virtual COM Port (UART0)** is wired
to **PTB16** and **PTB17**. We can manually create a selection file for our tool.

The `board_config.yaml` follows:

```json
{
  "board_config": {
    "UART0_RX": "PTB16",
    "UART0_TX": "PTB17",
    "GPIOB_22": "PTB22",
    "GPIOB_21": "PTB21"
  }
}
```


The `GPIOB_22` should be split into:

* Peripheral: `GPIOB`
* Signal: `GPIO` (then find the entry where `base_pin == PTB22`)

```yaml
  GPIOB:
    GPIO:
    - base_pin: PTB22
      is_routable: true
      mux_value: '0x1'
      alt_mode: alt1
      coords: '68'
      func_label: PTB22
      description: General purpose IO, Port B, bit 22
```


The `UART0_RX` should be split into:

* Peripheral: `UART0`
* Signal: `RX` (then find the entry where `base_pin == PTB16`)

```yaml
  UART0:
    RX:
    - base_pin: PTB16
      is_routable: true
      mux_value: '0x3'
      alt_mode: alt3
      coords: '62'
      func_label: UART0_RX
      description: Receive data
```


The below is invalid because `RED_LED` and `BLUE_LED` are aliases that the signal configuration does not know about.

```json
{
  "board_config": {
    "UART0_RX": "PTB16",
    "UART0_TX": "PTB17",
    "RED_LED":  "PTB22",
    "BLUE_LED": "PTB21"
  }
}
```

### The Mapping Logic

We can now use the `parse_signal_to_pin_map` results to find the MUX values for these K64F pins.

The processing pipeline follows:

1. **Input:** `k64f_board_config` (manual list via JSON).
2. **Lookup:** Searches `mapping["UART0"]["RX"]`.
3. **Match:** It finds the entry where `base_pin == "PTB16"`.
4. **Extract:** It pulls `mux_value: "0x3"` and `alt_mode: "alt3"`.
5. **Output:** It writes the DTS line.

### Sample Pinctrl Result for K64F

If the tool runs correctly, it should output something like this for the K64F's Debug UART:

```c
/* Generated for FRDM-K64F UART0 */
&pinctrl {
    uart0_default: uart0_default {
        group1 {
            pinmux = <K64F_PORTB_PIN16_MUX_ALT3>, /* RX */
                     <K64F_PORTB_PIN17_MUX_ALT3>; /* TX */
            drive-strength = "low";
            bias-pull-up;
        };
    };
};
```
