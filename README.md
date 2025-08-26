# VHDL Testbench Generator

A Rust CLI tool for automatically generating VHDL testbenches from entity files with support for template generation, configuration-based test vectors, and self-checking testbenches.

## Features

- **🏗️ VHDL Template Generation**: Create complete VHDL entity templates with proper structure
- **⚙️ Configuration Generation**: Auto-generate baseline TOML configs from existing VHDL
- **🧪 Testbench Generation**: Create comprehensive testbenches with test vectors
- **📋 Self-Checking Tests**: Support for assert statements and expected output validation
- **🎯 Flexible Templates**: Customizable template system for different coding standards

## Installation

```bash
cargo build --release
```

The binary will be created as `target/release/autobench`.

## Workflows

### 🏗️ Start from Scratch (Template Generation)

Perfect when you're starting a new VHDL design:

```bash
# 1. Generate a VHDL entity template
./autobench --generate-template my_processor

# 2. Edit my_processor.vhd to implement your design
# (Add your ports, generics, and logic)

# 3. Generate baseline configuration
./autobench -i my_processor.vhd -g

# 4. Edit my_processor_config.toml to add test vectors

# 5. Generate the testbench
./autobench -i my_processor.vhd -c my_processor_config.toml
```

### 📄 Work with Existing VHDL

When you already have a VHDL file:

```bash
# 1. Generate baseline configuration from existing VHDL
./autobench -i stack.vhd -g

# 2. Edit stack_config.toml to customize tests

# 3. Generate testbench
./autobench -i stack.vhd -c stack_config.toml
```

## Command Line Options

```
Usage: autobench [OPTIONS]

Options:
  -i, --input <FILE>                    Input VHDL file to parse
  -o, --output <FILE>                   Output testbench file (default: <entity_name>_tb.vhd)
  -c, --config <FILE>                   Optional TOML configuration file
  -t, --template <FILE>                 Custom testbench template file
  -v, --verbose                         Enable verbose output
  -g, --generate-config                 Generate a baseline TOML configuration file and exit
      --generate-template <ENTITY_NAME> Generate a VHDL entity template and exit
  -h, --help                            Print help
  -V, --version                         Print version
```

## Examples

### Template Generation

```bash
# Create a new VHDL entity template
./autobench --generate-template uart_controller -v

# This creates uart_controller.vhd with proper structure
```

### Configuration Generation

```bash
# Generate config from existing VHDL file
./autobench -i counter.vhd -g -v

# Creates counter_config.toml with sensible defaults
```

### Full Testbench Generation

```bash
# Generate comprehensive testbench
./autobench -i fifo.vhd -c fifo_config.toml -o fifo_testbench.vhd -v
```

### Custom Templates

```bash
# Use custom testbench template
./autobench -i processor.vhd -t ./templates/custom_tb.vhdl -c processor_config.toml
```

## Generated VHDL Template Structure

The `--generate-template` creates a complete VHDL file with:

```vhdl
-- Professional header with entity name
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity my_entity is
    Generic (
        -- Example generics with comments
    );
    Port (
        -- Clock and reset (always included)
        clk : in STD_LOGIC;
        rst : in STD_LOGIC;
        
        -- Commented examples for inputs/outputs
    );
end entity my_entity;

architecture RTL of my_entity is
    -- Signal declarations section
begin
    -- Clocked process with reset
    -- Combinatorial logic section
end architecture RTL;
```

## Configuration File Format

Auto-generated configurations include:

```toml
# Timing configuration
clock_period_ns = 10      # 100 MHz clock
reset_duration_ns = 100

# Generic parameter mappings
[generics]
DATA_WIDTH = "32"
BUFFER_DEPTH = "8"

# Test vectors with expected outputs
[[test_vectors]]
time_ns = 100
description = "Sample test case - modify as needed"

[test_vectors.inputs]
enable = "0"
data_in = "\"00000000\""

[test_vectors.expected_outputs]
ready = "1"
data_out = "\"00000001\""

# Additional test vectors...
[[test_vectors]]
time_ns = 200
description = "Second test case"
# ... more test data
```

## Directory Structure

```
project/
├── src/
│   └── main.rs              # The CLI tool source
├── target/
│   └── release/
│       └── autotest         # Compiled binary
├── examples/
│   ├── *.vhd               # Example VHDL files
│   └── *_config.toml       # Example configurations
├── Cargo.toml
└── README.md
```

## Advanced Features

### Automatic VHDL Parsing

- **Smart Entity Detection**: Finds entity declarations regardless of formatting
- **Generic Extraction**: Parses generics with default values
- **Complex Port Handling**: Supports ranges like `(DATA_WIDTH-1 downto 0)`
- **Comment Filtering**: Ignores VHDL comments during parsing

### Testbench Generation

- **Component Declarations**: Auto-generates proper component interfaces
- **Signal Creation**: Creates testbench signals with appropriate initialization
- **Port Mapping**: Connects entity ports to testbench signals
- **Clock Generation**: Configurable clock generation process
- **Test Vectors**: Self-checking stimulus with expected outputs
- **Professional Structure**: Follows VHDL best practices

### Template System

The tool uses a flexible template system with placeholders:

- `{component_name}`: Entity name
- `{ports}`: Formatted port declarations  
- `{internal_signals}`: Testbench signals with initialization
- `{port_connections}`: Port map connections
- `{clk_gen}`: Clock generation process
- `{stim_proc}`: Stimulus process with test vectors

### Configuration Intelligence

- **Smart Defaults**: Generates sensible default values for all port types
- **Type Awareness**: Different defaults for STD_LOGIC vs STD_LOGIC_VECTOR
- **Generic Mapping**: Automatically maps generics with default values
- **Test Structure**: Creates sample test vectors for immediate use

## Supported VHDL Features

✅ **Supported:**
- Standard entity/port declarations
- Generic parameters with defaults
- STD_LOGIC and STD_LOGIC_VECTOR types
- Complex port ranges and expressions
- IEEE standard library usage
- Multi-line declarations
- Various comment styles

❌ **Limitations:**
- Entity parsing only (not packages)
- Limited to IEEE standard types
- Custom types require manual template modification

## Error Handling

Clear error messages for:
- Missing or invalid VHDL files
- Malformed TOML configuration
- Missing template files
- VHDL parsing errors
- File I/O issues

## Development

### Building from Source

```bash
git clone <repository>
cd autotest
cargo build --release
```

### Running Tests

```bash
cargo test
```

### Dependencies

- `regex`: VHDL parsing
- `serde`: Configuration serialization
- `toml`: Configuration file format
- `clap`: Command line interface
