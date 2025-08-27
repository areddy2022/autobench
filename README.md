# VHDL Testbench Generator

A Python CLI tool for automatically generating VHDL testbenches from entity files with support for template generation, configuration-based test vectors, and self-checking testbenches.

## Features

- **🏗️ VHDL Template Generation**: Create complete VHDL entity templates with proper structure
- **⚙️ Configuration Generation**: Auto-generate baseline TOML configs from existing VHDL
- **🧪 Testbench Generation**: Create comprehensive testbenches with test vectors
- **📋 Self-Checking Tests**: Support for assert statements and expected output validation
- **🎯 Flexible Templates**: Customizable template system for different coding standards
- **🤖 AI-Powered Config Generation**: Use Google Vertex AI (Gemini) to intelligently generate test configurations
- **⚡ GHDL Integration**: Simulate testbenches, generate waveforms, and report test results automatically

## Installation

```bash
uv sync
```

The tool will be available as `autobench` after installation.

## Workflows

### 🏗️ Start from Scratch (Template Generation)

Perfect when you're starting a new VHDL design:

```bash
# 1. Generate a VHDL entity template
uv run autobench generate-template my_processor

# 2. Edit my_processor.vhd to implement your design
# (Add your ports, generics, and logic)

# 3. Generate baseline configuration
uv run autobench -i my_processor.vhd -g

# 4. Edit my_processor_config.toml to add test vectors

# 5. Generate the testbench
uv run autobench -i my_processor.vhd -c my_processor_config.toml
```

### 📄 Work with Existing VHDL

When you already have a VHDL file:

```bash
# 1. Generate baseline configuration from existing VHDL
uv run autobench -i stack.vhd -g

# 2. Edit stack_config.toml to customize tests

# 3. Generate testbench
uv run autobench -i stack.vhd -c stack_config.toml
```

### 🤖 AI-Powered Configuration (Recommended)

Let AI analyze your VHDL and generate intelligent test configurations:

```bash
# 1. Set up Google Cloud authentication
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-project-id"

# 2. Generate AI-powered configuration
uv run autobench generate-ai-config my_processor.vhd

# 3. Optional: provide additional requirements
uv run autobench generate-ai-config my_processor.vhd -p "Test edge cases for overflow and underflow"

# 4. Review and edit the generated *_ai_config.toml file

# 5. Generate testbench
uv run autobench -i my_processor.vhd -c my_processor_ai_config.toml

# 6. Run simulation and view results
uv run autobench simulate my_processor.vhd my_processor_tb.vhd
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
uv run autobench generate-template uart_controller -v

# This creates uart_controller.vhd with proper structure
```

### Configuration Generation

```bash
# Generate config from existing VHDL file
uv run autobench -i counter.vhd -g -v

# Creates counter_config.toml with sensible defaults
```

### Full Testbench Generation

```bash
# Generate comprehensive testbench
uv run autobench -i fifo.vhd -c fifo_config.toml -o fifo_testbench.vhd -v
```

### Custom Templates

```bash
# Use custom testbench template
uv run autobench -i processor.vhd -t ./templates/custom_tb.vhdl -c processor_config.toml
```

### AI Configuration Generation

```bash
# Basic AI config generation
uv run autobench generate-ai-config counter.vhd

# With specific requirements
uv run autobench generate-ai-config fifo.vhd -p "Test full and empty conditions, test FIFO overflow"

# With custom output file
uv run autobench generate-ai-config alu.vhd -o custom_alu_config.toml
```

### GHDL Simulation

```bash
# Basic simulation with waveform generation
uv run autobench simulate entity.vhd testbench.vhd

# Simulation with custom time and verbose output
uv run autobench simulate entity.vhd testbench.vhd --sim-time 500ns -v

# Skip waveform generation for faster simulation
uv run autobench simulate entity.vhd testbench.vhd --no-waveform

# Keep GHDL work files for debugging
uv run autobench simulate entity.vhd testbench.vhd --no-cleanup
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

### User-Friendly Syntax

The tool uses **automatic VHDL literal conversion** - you write simple values and the tool applies correct quoting:

```toml
[[test_vectors]]
time_ns = 100
description = "Test counter operation"

[test_vectors.inputs]
rst = "1"                # Simple values - no quotes needed!
enable = "0"             # Tool automatically converts to proper VHDL
data_in = "10101010"     # Bit patterns written naturally

[test_vectors.expected_outputs]  
count = "5"              # Numbers written simply
ready = "1"              # Tool handles STD_LOGIC vs STD_LOGIC_VECTOR
```

**Automatic Conversion to VHDL:**
- `rst = "1"` → `tb_rst <= '1';` (STD_LOGIC gets single quotes)
- `data_in = "10101010"` → `tb_data_in <= "10101010";` (STD_LOGIC_VECTOR gets double quotes)
- `count = "42"` → `tb_count <= 42;` (INTEGER gets no quotes)

**Generic Parameter Override:**
```toml
[generics]
DATA_WIDTH = "16"     # Override default value
DEPTH = "32"          # Override default value
```

Generates VHDL component with updated generics:
```vhdl
component my_entity is
    Generic (
        DATA_WIDTH : INTEGER := 16;  -- Config value used
        DEPTH : INTEGER := 32         -- Config value used
    );
    -- ...
end component;

-- And proper instantiation:
uut: my_entity 
    generic map(
        DATA_WIDTH => 16,
        DEPTH => 32
    )
    port map( /* ... */ );
```

### Generated Configuration Structure

Auto-generated configurations include:

```toml
# Timing configuration
clock_period_ns = 10      # 100 MHz clock
reset_duration_ns = 100

# Generic parameter mappings
[generics]
DATA_WIDTH = "32"
BUFFER_DEPTH = "8"

# Test vectors with absolute timing
[[test_vectors]]
time_ns = 100             # Apply this test at 100ns absolute time
description = "First test at 100ns"

[test_vectors.inputs]
enable = "1"
data_in = "10101010"

[test_vectors.expected_outputs]
ready = "1"

# Second test vector at absolute time 250ns  
[[test_vectors]]
time_ns = 250             # Apply this test at 250ns absolute time (150ns after first)
description = "Second test at 250ns"

[test_vectors.inputs] 
enable = "0"              # Only change what's different

[test_vectors.expected_outputs]
ready = "0"
```

## Directory Structure

```
project/
├── autobench/
│   ├── __init__.py         # Package initialization
│   ├── main.py            # CLI entry point
│   ├── vhdl_parser.py     # VHDL parsing logic
│   ├── config.py          # Configuration handling
│   ├── testbench_generator.py  # Testbench generation
│   └── templates.py       # Template management
├── tests/
│   ├── test_vhdl_parser.py    # Parser tests
│   └── test_testbench_generator.py  # Generator tests
├── template/              # Template files
├── pyproject.toml        # Python project configuration
└── README.md
```

## AI Configuration Generation

The AI-powered configuration generator uses Google Vertex AI (Gemini) to analyze your VHDL code and create intelligent test configurations:

### Key Features

- **Smart Entity Analysis**: AI understands component purpose from entity names and port patterns
- **Intelligent Test Vectors**: Generates comprehensive test cases based on component type (counters, FIFOs, ALUs, etc.)
- **Realistic Timing**: Appropriate clock periods and timing based on complexity
- **Edge Case Testing**: Automatically includes boundary conditions and corner cases
- **Descriptive Test Names**: Generated test vectors include meaningful descriptions
- **Optimized Test Vectors**: Only includes inputs that change between test steps (VHDL signals maintain values)
- **Automatic VHDL Syntax**: Users write simple values (0, 1, 10101010) - tool automatically applies correct quoting
- **Generic Parameter Support**: Override generic values in config, automatically applied to component declaration and instantiation

### Setup

1. **Install Google Cloud CLI**: [Download from Google Cloud](https://cloud.google.com/sdk/docs/install)
2. **Authenticate**:
   ```bash
   gcloud auth application-default login
   ```
3. **Set Project ID**:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```
4. **Enable Vertex AI API**: Visit [Google Cloud Console](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com)
5. **Use AI Generation**:
   ```bash
   uv run autobench generate-ai-config your_entity.vhd
   ```

### Example AI-Generated Config

For a FIFO entity, the AI might generate:

```toml
clock_period_ns = 10
reset_duration_ns = 100

[generics]
DATA_WIDTH = "8"
FIFO_DEPTH = "16"

[[test_vectors]]
time_ns = 50
description = "Test reset behavior - all outputs should be in reset state"
[test_vectors.inputs]
write_enable = "0"           # Simple value - tool adds quotes automatically
read_enable = "0"            # Simple value - tool adds quotes automatically  
data_in = "00000000"         # Simple value - tool adds quotes automatically
[test_vectors.expected_outputs]
empty = "1"                  # Simple value - tool adds quotes automatically
full = "0"                   # Simple value - tool adds quotes automatically

[[test_vectors]]
time_ns = 100
description = "Test single write operation"
[test_vectors.inputs]
write_enable = "1"           # Simple value - tool adds quotes automatically
data_in = "10101010"         # Simple value - tool adds quotes automatically
# Second test vector - only change what's different  
[[test_vectors]]
time_ns = 100
description = "Write first data word"
[test_vectors.inputs]
write_enable = "1"            # Simple value - tool adds quotes automatically
data_in = "10101010"          # Simple value - tool adds quotes automatically
# Note: read_enable stays 0 from previous vector

[[test_vectors]]
time_ns = 150  
description = "Switch to read mode"
[test_vectors.inputs]
write_enable = "0"            # Simple value - tool adds quotes automatically
read_enable = "1"             # Simple value - tool adds quotes automatically
# Note: data_in maintains 10101010 value
[test_vectors.expected_outputs]
data_out = "10101010"         # Simple value - tool adds quotes automatically
empty = "0"                   # Simple value - tool adds quotes automatically
```

## GHDL Simulation Integration

The tool includes built-in GHDL integration for automatic testbench simulation and verification:

### Prerequisites

1. **Install GHDL**: [Download from GHDL website](http://ghdl.free.fr/) or use package manager:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ghdl
   
   # macOS with Homebrew
   brew install ghdl
   
   # Verify installation
   ghdl --version
   ```

2. **Optional: Install GTKWave** for waveform viewing:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install gtkwave
   
   # macOS with Homebrew  
   brew install gtkwave
   ```

### Key Features

- **Automatic Compilation**: Compiles entity and testbench files with proper dependencies
- **Waveform Generation**: Creates .ghw files for GTKWave inspection
- **Test Result Parsing**: Extracts assertion results and test pass/fail status
- **Clean Output**: User-friendly reporting of simulation results
- **Error Handling**: Clear error messages for compilation and simulation issues

### Usage Examples

```bash
# Complete workflow example
uv run autobench generate-template counter
# Edit counter.vhd to implement your design
uv run autobench -i counter.vhd -g
# Edit counter_config.toml with test cases
uv run autobench -i counter.vhd -c counter_config.toml
# Run simulation
uv run autobench simulate counter.vhd counter_tb.vhd

# Output example:
# ✅ Simulation completed successfully
# 
# 📊 Test Results: 4/5 passed
#   ✅ PASS: Test 1 @100ns  
#   ✅ PASS: Test 2 @200ns
#   ❌ FAIL: Test 3 @300ns
#   ✅ PASS: Test 4 @400ns
#   ✅ PASS: Test 5 @500ns
#
# ❌ 1 test(s) failed
#
# 🌊 Waveform saved: counter_tb.ghw
#    Open with: gtkwave counter_tb.ghw
```

### Self-Checking Testbenches

The tool automatically detects VHDL assertions in your testbench:

```vhdl
-- In your testbench
assert output_count = expected_value
    report "Test 1: Counter mismatch - expected " & 
           integer'image(expected_value) & 
           ", got " & integer'image(output_count)
    severity error;
```

The simulation runner will:
- Parse assertion outputs
- Report pass/fail status for each test
- Show timing information
- Provide detailed error messages for failures

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
cd autobench
uv sync
```

### Running Tests

```bash
uv run pytest
```

### Dependencies

- `click`: Command line interface
- `tomli-w`: TOML file writing
- `google-cloud-aiplatform`: Google Vertex AI client for AI features
- `pytest`: Testing framework
