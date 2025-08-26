use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

// Cargo.toml dependencies needed:
// [dependencies]
// regex = "1.0"
// serde = { version = "1.0", features = ["derive"] }
// toml = "0.8"
// clap = { version = "4.0", features = ["derive"] }

// Default template bundled into the binary
const DEFAULT_TEMPLATE: &str = r#"--=============================================================================
--Library Declarations:
--=============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use ieee.math_real.all;
library UNISIM;
use UNISIM.VComponents.all;
--=============================================================================
--Entity Declaration:
--=============================================================================
entity {component_name}_tb is
end entity;
--=============================================================================
--Architecture
--=============================================================================
architecture testbench of {component_name}_tb is
--=============================================================================
--Component Declaration
--=============================================================================
component {component_name} is
    Port ( 
{ports}
         );
end component;
--=============================================================================
--Signals
--=============================================================================
{internal_signals}
begin
--=============================================================================
--Port Map
--=============================================================================
uut: {component_name} 
	port map(		
{port_connections});
--=============================================================================
--clk_100MHz generation 
--=============================================================================
clkgen_proc: process
begin
{clk_gen}
end process clkgen_proc;
--=============================================================================
--Stimulus Process
--=============================================================================
stim_proc: process
begin				
{stim_proc}
    wait;
end process stim_proc;
end testbench;"#;

use clap::{Arg, Command};

// Alternative: Load template from file at compile time
// const DEFAULT_TEMPLATE: &str = include_str!("../template/template_tb.vhdl");

#[derive(Debug, Clone)]
pub struct VhdlPort {
    pub name: String,
    pub direction: String,     // "in", "out", "inout"
    pub signal_type: String,   // "STD_LOGIC", "STD_LOGIC_VECTOR", etc.
    pub range: Option<String>, // e.g., "(DATA_WIDTH-1 downto 0)"
}

#[derive(Debug, Clone)]
pub struct VhdlGeneric {
    pub name: String,
    pub generic_type: String,
    pub default_value: Option<String>,
}

#[derive(Debug)]
pub struct VhdlEntity {
    pub name: String,
    pub generics: Vec<VhdlGeneric>,
    pub ports: Vec<VhdlPort>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct TestVector {
    pub time_ns: u32,
    pub inputs: HashMap<String, String>,
    pub expected_outputs: Option<HashMap<String, String>>,
    pub description: Option<String>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct TestbenchConfig {
    pub clock_period_ns: Option<u32>,
    pub reset_duration_ns: Option<u32>,
    pub test_vectors: Option<Vec<TestVector>>,
    pub generics: Option<HashMap<String, String>>,
}

pub struct VhdlParser;

impl VhdlParser {
    pub fn parse_file<P: AsRef<Path>>(path: P) -> Result<VhdlEntity, Box<dyn std::error::Error>> {
        let path = path.as_ref();
        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read VHDL file '{}': {}", path.display(), e))?;
        Self::parse_content(&content).map_err(|e| -> Box<dyn std::error::Error> {
            format!("Failed to parse VHDL file '{}': {}", path.display(), e).into()
        })
    }

    pub fn parse_content(content: &str) -> Result<VhdlEntity, Box<dyn std::error::Error>> {
        // Remove comments and normalize whitespace
        let cleaned = Self::clean_content(content);

        // Extract entity name
        let entity_name = Self::extract_entity_name(&cleaned)?;

        // Extract generics
        let generics = Self::extract_generics(&cleaned)?;

        // Extract ports
        let ports = Self::extract_ports(&cleaned)?;

        Ok(VhdlEntity {
            name: entity_name,
            generics,
            ports,
        })
    }

    fn clean_content(content: &str) -> String {
        // Remove single-line comments
        let comment_re = Regex::new(r"--.*$").unwrap();
        let lines: Vec<String> = content
            .lines()
            .map(|line| comment_re.replace(line, "").to_string())
            .collect();

        // Join lines and normalize whitespace
        lines
            .join(" ")
            .split_whitespace()
            .collect::<Vec<&str>>()
            .join(" ")
            .to_lowercase()
    }

    fn extract_entity_name(content: &str) -> Result<String, Box<dyn std::error::Error>> {
        let re = Regex::new(r"entity\s+(\w+)\s+is")?;
        if let Some(caps) = re.captures(content) {
            Ok(caps[1].to_string())
        } else {
            Err("Could not find entity name".into())
        }
    }

    fn extract_generics(content: &str) -> Result<Vec<VhdlGeneric>, Box<dyn std::error::Error>> {
        let mut generics = Vec::new();

        // Look for generic section
        let generic_re = Regex::new(r"generic\s*\((.*?)\)\s*;")?;
        if let Some(caps) = generic_re.captures(content) {
            let generic_content = &caps[1];

            // Parse individual generics - handle both single line and multi-line declarations
            let generic_item_re = Regex::new(r"(\w+)\s*:\s*(\w+)(?:\s*:=\s*([^;,)]+))?")?;
            for caps in generic_item_re.captures_iter(generic_content) {
                let default_val = caps.get(3).map(|m| m.as_str().trim().to_string());
                generics.push(VhdlGeneric {
                    name: caps[1].to_string(),
                    generic_type: caps[2].to_string(),
                    default_value: default_val,
                });
            }
        }

        Ok(generics)
    }

    fn extract_ports(content: &str) -> Result<Vec<VhdlPort>, Box<dyn std::error::Error>> {
        let mut ports = Vec::new();

        // Find the start of the port section
        let port_start_re = Regex::new(r"(?i)port\s*\(")?;

        if let Some(start_match) = port_start_re.find(content) {
            let start_pos = start_match.end() - 1; // Position of the opening '('

            // Find the matching closing parenthesis using balanced counting
            let mut paren_count = 0;
            let mut end_pos = None;

            for (i, ch) in content[start_pos..].char_indices() {
                match ch {
                    '(' => paren_count += 1,
                    ')' => {
                        paren_count -= 1;
                        if paren_count == 0 {
                            end_pos = Some(start_pos + i);
                            break;
                        }
                    }
                    _ => {}
                }
            }

            if let Some(end) = end_pos {
                // Extract the content between the balanced parentheses
                let port_content = &content[start_pos + 1..end];

                eprintln!("Extracted port content: '{}'", port_content);

                // Split by semicolons, but be careful with parentheses in ranges
                let port_declarations = Self::split_port_declarations_improved(port_content);

                eprintln!("Split into {} declarations", port_declarations.len());

                for (i, decl) in port_declarations.iter().enumerate() {
                    eprintln!("Declaration {}: '{}'", i, decl);
                    if let Some(port) = Self::parse_port_declaration_improved(&decl) {
                        eprintln!("Successfully parsed: {:?}", port);
                        ports.push(port);
                    } else {
                        eprintln!("Failed to parse declaration: '{}'", decl);
                    }
                }
            } else {
                eprintln!("Could not find matching closing parenthesis for port section");
            }
        } else {
            eprintln!("No port section found in content");
        }

        eprintln!("Total ports parsed: {}", ports.len());
        Ok(ports)
    }

    fn split_port_declarations_improved(content: &str) -> Vec<String> {
        let mut declarations = Vec::new();
        let mut current = String::new();
        let mut paren_depth = 0;

        for ch in content.chars() {
            match ch {
                '(' => {
                    paren_depth += 1;
                    current.push(ch);
                }
                ')' => {
                    paren_depth -= 1;
                    current.push(ch);
                }
                ';' if paren_depth == 0 => {
                    if !current.trim().is_empty() {
                        declarations.push(current.trim().to_string());
                        current.clear();
                    }
                }
                _ => current.push(ch),
            }
        }

        // Handle the last declaration if it doesn't end with semicolon
        if !current.trim().is_empty() {
            declarations.push(current.trim().to_string());
        }

        declarations
    }

    fn parse_port_declaration_improved(decl: &str) -> Option<VhdlPort> {
        // Clean up the declaration
        let cleaned = decl.trim().replace('\n', " ").replace('\r', "");
        let cleaned = cleaned.split_whitespace().collect::<Vec<&str>>().join(" ");

        eprintln!("Parsing cleaned declaration: '{}'", cleaned);

        // More flexible regex that handles ranges better
        let port_re =
            Regex::new(r"(?i)(\w+)\s*:\s*(in|out|inout)\s+(\w+(?:_\w+)*)(?:\s*(\([^)]*\)))?")
                .ok()?;

        if let Some(caps) = port_re.captures(&cleaned) {
            let range = caps.get(4).map(|m| {
                let range_str = m.as_str();
                eprintln!("Captured range: '{}'", range_str);
                range_str.to_string()
            });

            Some(VhdlPort {
                name: caps[1].to_lowercase(),
                direction: caps[2].to_lowercase(),
                signal_type: caps[3].to_lowercase(),
                range,
            })
        } else {
            eprintln!("Regex didn't match for: '{}'", cleaned);
            None
        }
    }
}

pub struct TestbenchGenerator;

impl TestbenchGenerator {
    pub fn generate_testbench_data(
        entity: &VhdlEntity,
        config: Option<&TestbenchConfig>,
    ) -> TestbenchData {
        let component_name = &entity.name;
        let ports = Self::generate_ports_string(&entity.ports, &entity.generics, config);
        let internal_signals =
            Self::generate_internal_signals(&entity.ports, &entity.generics, config);
        let port_connections = Self::generate_port_connections(&entity.ports);
        let clk_gen = Self::generate_clock_generation(config);
        let stim_proc = Self::generate_stimulus_process(&entity.ports, config);

        TestbenchData {
            component_name: component_name.clone(),
            ports,
            internal_signals,
            port_connections,
            clk_gen,
            stim_proc,
        }
    }

    fn generate_ports_string(
        ports: &[VhdlPort],
        generics: &[VhdlGeneric],
        config: Option<&TestbenchConfig>,
    ) -> String {
        let mut result = String::new();

        for (i, port) in ports.iter().enumerate() {
            result.push_str(&format!(
                "        {} : {} {}",
                port.name,
                port.direction.to_uppercase(),
                port.signal_type.to_uppercase()
            ));

            if let Some(range) = &port.range {
                // Resolve generic parameters in ranges
                let resolved_range = Self::resolve_generic_range(range, generics, config);
                result.push_str(&resolved_range);
            }

            if i < ports.len() - 1 {
                result.push_str(";\n");
            } else {
                result.push('\n');
            }
        }

        result
    }

    fn resolve_generic_range(
        range: &str,
        generics: &[VhdlGeneric],
        config: Option<&TestbenchConfig>,
    ) -> String {
        let mut resolved = range.to_string();
        let default_value = "32";

        // Replace generic parameters with their values
        for generic in generics {
            let generic_name = &generic.name.to_uppercase();

            // Check if config overrides this generic
            let value = if let Some(config) = config {
                // First try to get from config
                if let Some(config_value) = config
                    .generics
                    .as_ref()
                    .and_then(|g| g.get(&generic.name).or_else(|| g.get(generic_name)))
                {
                    config_value.as_str()
                } else {
                    // Fall back to generic default value
                    generic.default_value.as_deref().unwrap_or(default_value)
                }
            } else {
                generic.default_value.as_deref().unwrap_or(default_value)
            };

            // Replace both uppercase and original case
            resolved = resolved.replace(generic_name, value);
            resolved = resolved.replace(&generic.name, value);
        }

        resolved
    }

    fn generate_internal_signals(
        ports: &[VhdlPort],
        generics: &[VhdlGeneric],
        config: Option<&TestbenchConfig>,
    ) -> String {
        let mut signals = Vec::new();

        for port in ports {
            let signal_name = format!("tb_{}", port.name);
            let mut signal_decl = format!(
                "signal {} : {}",
                signal_name,
                port.signal_type.to_uppercase()
            );

            if let Some(range) = &port.range {
                // Resolve generic parameters in ranges
                let resolved_range = Self::resolve_generic_range(range, generics, config);
                signal_decl.push_str(&resolved_range);
            }

            // Add default values for testbench signals
            match port.signal_type.to_uppercase().as_str() {
                "STD_LOGIC" => signal_decl.push_str(" := '0'"),
                "STD_LOGIC_VECTOR" => signal_decl.push_str(" := (others => '0')"),
                "INTEGER" => signal_decl.push_str(" := 0"),
                _ => signal_decl.push_str(" := '0'"),
            }

            signal_decl.push(';');
            signals.push(signal_decl);
        }

        // Add clock signal if not present
        if !ports.iter().any(|p| p.name.to_lowercase().contains("clk")) {
            signals.push("signal tb_clk : STD_LOGIC := '0';".to_string());
        }

        signals.join("\n")
    }

    fn generate_port_connections(ports: &[VhdlPort]) -> String {
        let mut connections = Vec::new();

        for (i, port) in ports.iter().enumerate() {
            let connection = format!("        {} => tb_{}", port.name, port.name);
            if i < ports.len() - 1 {
                connections.push(format!("{},", connection));
            } else {
                connections.push(connection);
            }
        }

        connections.join("\n")
    }

    fn generate_clock_generation(config: Option<&TestbenchConfig>) -> String {
        let period = config.and_then(|c| c.clock_period_ns).unwrap_or(10); // Default 10ns period (100MHz)

        let half_period = period / 2;

        format!(
            "    tb_clk <= '0';\n    wait for {} ns;\n    tb_clk <= '1';\n    wait for {} ns;",
            half_period, half_period
        )
    }

    fn generate_stimulus_process(ports: &[VhdlPort], config: Option<&TestbenchConfig>) -> String {
        let mut stimulus = String::new();

        // Reset sequence
        let reset_duration = config.and_then(|c| c.reset_duration_ns).unwrap_or(100);

        stimulus.push_str(&format!(
            "    -- Reset sequence\n    tb_rst <= '1';\n    wait for {} ns;\n    tb_rst <= '0';\n    wait for 20 ns;\n\n",
            reset_duration
        ));

        // Generate test vectors if provided in config
        if let Some(config) = config {
            if let Some(test_vectors) = &config.test_vectors {
                stimulus.push_str("    -- Test vectors\n");

                for (i, vector) in test_vectors.iter().enumerate() {
                    if let Some(desc) = &vector.description {
                        stimulus.push_str(&format!("    -- Test {}: {}\n", i + 1, desc));
                    } else {
                        stimulus.push_str(&format!("    -- Test vector {}\n", i + 1));
                    }

                    // Apply inputs
                    for (signal, value) in &vector.inputs {
                        stimulus.push_str(&format!("    tb_{} <= {};\n", signal, value));
                    }

                    stimulus.push_str(&format!("    wait for {} ns;\n", vector.time_ns));

                    // Check expected outputs if provided
                    if let Some(expected) = &vector.expected_outputs {
                        for (signal, expected_value) in expected {
                            // Determine the signal type for proper formatting
                            let format_func = if expected_value.starts_with("x\"")
                                || expected_value.contains("downto")
                            {
                                "to_hstring" // For vectors
                            } else {
                                "std_logic'image" // For single bits
                            };

                            stimulus.push_str(&format!(
                                "    assert tb_{} = {} report \"Expected {} = {}, got \" & {}(tb_{}) severity error;\n",
                                signal, expected_value, signal, expected_value, format_func, signal
                            ));
                        }
                    }

                    stimulus.push('\n');
                }
            } else {
                // Generate basic test sequence for stack
                stimulus.push_str(&Self::generate_basic_stack_test(ports));
            }
        } else {
            // Generate basic test sequence
            stimulus.push_str(&Self::generate_basic_test(ports));
        }

        stimulus.push_str("    -- End of test\n    report \"Test completed\" severity note;\n");
        stimulus
    }

    fn generate_basic_stack_test(_ports: &[VhdlPort]) -> String {
        let mut test = String::new();

        test.push_str("    -- Basic stack test\n");
        test.push_str("    -- Test push operation\n");
        test.push_str("    tb_push <= '1';\n");
        test.push_str("    tb_pop <= '0';\n");
        test.push_str("    tb_data_in <= x\"DEADBEEF\";\n");
        test.push_str("    wait for 20 ns;\n");
        test.push_str("    tb_push <= '0';\n");
        test.push_str("    wait for 20 ns;\n\n");

        test.push_str("    -- Test pop operation\n");
        test.push_str("    tb_pop <= '1';\n");
        test.push_str("    wait for 20 ns;\n");
        test.push_str("    tb_pop <= '0';\n");
        test.push_str("    wait for 20 ns;\n\n");

        test
    }

    fn generate_basic_test(ports: &[VhdlPort]) -> String {
        let mut test = String::new();

        test.push_str("    -- Basic stimulus\n");

        for port in ports {
            if port.direction == "in" && port.name != "clk" && port.name != "rst" {
                match port.signal_type.to_uppercase().as_str() {
                    "STD_LOGIC" => {
                        test.push_str(&format!("    tb_{} <= '1';\n", port.name));
                        test.push_str("    wait for 20 ns;\n");
                        test.push_str(&format!("    tb_{} <= '0';\n", port.name));
                        test.push_str("    wait for 20 ns;\n");
                    }
                    "STD_LOGIC_VECTOR" => {
                        test.push_str(&format!("    tb_{} <= (others => '1');\n", port.name));
                        test.push_str("    wait for 20 ns;\n");
                        test.push_str(&format!("    tb_{} <= (others => '0');\n", port.name));
                        test.push_str("    wait for 20 ns;\n");
                    }
                    _ => {}
                }
            }
        }

        test.push('\n');
        test
    }
}

#[derive(Debug)]
pub struct TestbenchData {
    pub component_name: String,
    pub ports: String,
    pub internal_signals: String,
    pub port_connections: String,
    pub clk_gen: String,
    pub stim_proc: String,
}

impl TestbenchData {
    pub fn apply_to_template(&self, template: &str) -> String {
        template
            .replace("{component_name}", &self.component_name)
            .replace("{ports}", &self.ports)
            .replace("{internal_signals}", &self.internal_signals)
            .replace("{port_connections}", &self.port_connections)
            .replace("{clk_gen}", &self.clk_gen)
            .replace("{stim_proc}", &self.stim_proc)
    }
}

pub fn load_config<P: AsRef<Path>>(path: P) -> Result<TestbenchConfig, Box<dyn std::error::Error>> {
    let path = path.as_ref();
    let content = fs::read_to_string(path)
        .map_err(|e| format!("Failed to read config file '{}': {}", path.display(), e))?;
    let config: TestbenchConfig =
        toml::from_str(&content).map_err(|e| -> Box<dyn std::error::Error> {
            format!("Failed to parse TOML config '{}': {}", path.display(), e).into()
        })?;
    Ok(config)
}

pub fn generate_baseline_config(entity: &VhdlEntity) -> TestbenchConfig {
    // Create a sample test vector
    let mut sample_inputs = HashMap::new();
    let mut expected_outputs = HashMap::new();
    
    // Add sample values for input ports
    for port in &entity.ports {
        match port.direction.as_str() {
            "in" => {
                let sample_value = match port.signal_type.as_str() {
                    "std_logic" => "0".to_string(),
                    "std_logic_vector" => {
                        if port.range.is_some() {
                            "\"00000000\"".to_string() // Default 8-bit vector
                        } else {
                            "\"0\"".to_string()
                        }
                    }
                    _ => "0".to_string(),
                };
                sample_inputs.insert(port.name.clone(), sample_value);
            }
            "out" => {
                let expected_value = match port.signal_type.as_str() {
                    "std_logic" => "0".to_string(),
                    "std_logic_vector" => {
                        if port.range.is_some() {
                            "\"00000000\"".to_string() // Default 8-bit vector
                        } else {
                            "\"0\"".to_string()
                        }
                    }
                    _ => "0".to_string(),
                };
                expected_outputs.insert(port.name.clone(), expected_value);
            }
            _ => {}
        }
    }
    
    let sample_test_vector = TestVector {
        time_ns: 100,
        inputs: sample_inputs,
        expected_outputs: Some(expected_outputs),
        description: Some("Sample test case - modify as needed".to_string()),
    };
    
    // Create generic mappings from entity generics
    let mut generics_map = HashMap::new();
    for generic in &entity.generics {
        if let Some(default_val) = &generic.default_value {
            generics_map.insert(generic.name.clone(), default_val.clone());
        }
    }
    
    TestbenchConfig {
        clock_period_ns: Some(10), // 10ns = 100MHz
        reset_duration_ns: Some(100),
        test_vectors: Some(vec![sample_test_vector]),
        generics: if generics_map.is_empty() { None } else { Some(generics_map) },
    }
}

pub fn save_config<P: AsRef<Path>>(config: &TestbenchConfig, path: P) -> Result<(), Box<dyn std::error::Error>> {
    let path = path.as_ref();
    let toml_content = toml::to_string_pretty(config)
        .map_err(|e| format!("Failed to serialize config to TOML: {}", e))?;
    fs::write(path, toml_content)
        .map_err(|e| format!("Failed to write config file '{}': {}", path.display(), e))?;
    Ok(())
}

pub fn generate_vhdl_template(entity_name: &str) -> String {
    format!(r#"-- =============================================================================
-- VHDL Entity Template
-- Entity: {entity_name}
-- =============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

-- =============================================================================
-- Entity Declaration
-- =============================================================================
entity {entity_name} is
    Generic (
        -- Add your generics here
        -- DATA_WIDTH : INTEGER := 32;
        -- DEPTH      : INTEGER := 16
    );
    Port (
        -- Clock and Reset
        clk : in STD_LOGIC;
        rst : in STD_LOGIC;
        
        -- Add your input ports here
        -- enable     : in  STD_LOGIC;
        -- data_in    : in  STD_LOGIC_VECTOR(DATA_WIDTH-1 downto 0);
        
        -- Add your output ports here
        -- ready      : out STD_LOGIC;
        -- data_out   : out STD_LOGIC_VECTOR(DATA_WIDTH-1 downto 0)
    );
end entity {entity_name};

-- =============================================================================
-- Architecture Declaration
-- =============================================================================
architecture RTL of {entity_name} is
    
    -- Internal signals
    -- signal internal_reg : STD_LOGIC_VECTOR(DATA_WIDTH-1 downto 0) := (others => '0');
    -- signal counter      : UNSIGNED(7 downto 0) := (others => '0');
    
begin
    
    -- ==========================================================================
    -- Main Process
    -- ==========================================================================
    main_process : process(clk)
    begin
        if rising_edge(clk) then
            if rst = '1' then
                -- Reset logic here
                -- internal_reg <= (others => '0');
                -- counter <= (others => '0');
            else
                -- Main logic here
                
            end if;
        end if;
    end process main_process;
    
    -- ==========================================================================
    -- Combinatorial Logic
    -- ==========================================================================
    -- Add your combinatorial assignments here
    -- data_out <= internal_reg;
    -- ready <= '1' when counter = 0 else '0';
    
end architecture RTL;
"#)
}

pub fn save_vhdl_template<P: AsRef<Path>>(entity_name: &str, path: P) -> Result<(), Box<dyn std::error::Error>> {
    let path = path.as_ref();
    let template_content = generate_vhdl_template(entity_name);
    fs::write(path, template_content)
        .map_err(|e| format!("Failed to write VHDL template file '{}': {}", path.display(), e))?;
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let matches = Command::new("VHDL Testbench Generator")
        .version("1.0")
        .author("Your Name")
        .about("Generates VHDL testbenches from entity files")
        .after_help("WORKFLOWS:\n\n  Template Generation:\n    1. Generate VHDL template: tool --generate-template my_entity\n    2. Edit my_entity.vhd to implement your design\n    3. Generate config: tool -i my_entity.vhd -g\n    4. Edit config and generate testbench: tool -i my_entity.vhd -c my_entity_config.toml\n\n  Existing VHDL:\n    1. Generate baseline config: tool -i input.vhd -g\n    2. Edit the generated config file\n    3. Generate testbench: tool -i input.vhd -c input_config.toml")
        .arg(
            Arg::new("input")
                .short('i')
                .long("input")
                .value_name("FILE")
                .help("Input VHDL file to parse")
                .required_unless_present("generate_template"),
        )
        .arg(
            Arg::new("output")
                .short('o')
                .long("output")
                .value_name("FILE")
                .help("Output testbench file (default: <entity_name>_tb.vhd)"),
        )
        .arg(
            Arg::new("config")
                .short('c')
                .long("config")
                .value_name("FILE")
                .help("Optional TOML configuration file"),
        )
        .arg(
            Arg::new("template")
                .short('t')
                .long("template")
                .value_name("FILE")
                .help("Custom template file (uses bundled default if not specified)"),
        )
        .arg(
            Arg::new("verbose")
                .short('v')
                .long("verbose")
                .help("Enable verbose output")
                .action(clap::ArgAction::SetTrue),
        )
        .arg(
            Arg::new("generate_config")
                .short('g')
                .long("generate-config")
                .help("Generate a baseline TOML configuration file and exit")
                .action(clap::ArgAction::SetTrue),
        )
        .arg(
            Arg::new("generate_template")
                .long("generate-template")
                .value_name("ENTITY_NAME")
                .help("Generate a VHDL entity template with the specified name and exit"),
        )
        .get_matches();

    let input_file = matches.get_one::<String>("input");
    let verbose = matches.get_flag("verbose");
    let generate_config = matches.get_flag("generate_config");
    let generate_template = matches.get_one::<String>("generate_template");

    // If generate-template flag is set, generate VHDL template and exit
    if let Some(entity_name) = generate_template {
        let template_filename = format!("{}.vhd", entity_name);
        
        save_vhdl_template(entity_name, &template_filename)?;
        
        println!("Generated VHDL template file: {}", template_filename);
        if verbose {
            println!("Edit this file to implement your VHDL entity.");
            println!("After implementation, generate config with: --generate-config -i {}", template_filename);
        }
        return Ok(());
    }

    let input_file = input_file.unwrap(); // Safe to unwrap now due to required_unless_present
    
    if verbose {
        println!("Parsing VHDL file: {}", input_file);
    }

    // Parse VHDL file
    let entity = VhdlParser::parse_file(input_file)?;

    if verbose {
        println!("Parsed entity: {}", entity.name);
        println!("  Generics: {}", entity.generics.len());
        println!("  Ports: {}", entity.ports.len());
    }

    // If generate-config flag is set, generate baseline config and exit
    if generate_config {
        let baseline_config = generate_baseline_config(&entity);
        let config_filename = format!("{}_config.toml", entity.name);
        
        save_config(&baseline_config, &config_filename)?;
        
        println!("Generated baseline configuration file: {}", config_filename);
        if verbose {
            println!("Edit this file to customize your test vectors and parameters,");
            println!("then run the generator again with: -i {} -c {}", input_file, config_filename);
        }
        return Ok(());
    }

    // Load optional config
    let config = if let Some(config_file) = matches.get_one::<String>("config") {
        if verbose {
            println!("Loading config from: {}", config_file);
        }
        Some(load_config(config_file)?)
    } else {
        // Try to find a default config file
        let default_config = format!("{}_config.toml", entity.name);
        if Path::new(&default_config).exists() {
            if verbose {
                println!("Found default config: {}", default_config);
            }
            Some(load_config(&default_config)?)
        } else {
            None
        }
    };

    // Generate testbench data
    let testbench_data = TestbenchGenerator::generate_testbench_data(&entity, config.as_ref());

    // Load template
    let template = if let Some(template_file) = matches.get_one::<String>("template") {
        // Use custom template file
        if verbose {
            println!("Loading custom template from: {}", template_file);
        }
        fs::read_to_string(template_file)
            .map_err(|e| format!("Failed to read template file '{}': {}", template_file, e))?
    } else {
        // Use bundled default template
        if verbose {
            println!("Using bundled default template");
        }
        DEFAULT_TEMPLATE.to_string()
    };

    // Generate final testbench
    let final_testbench = testbench_data.apply_to_template(&template);

    // Determine output file
    let output_file = matches
        .get_one::<String>("output")
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("{}_tb.vhd", entity.name));

    // Write to file
    fs::write(&output_file, final_testbench)?;

    println!("Testbench generated successfully: {}", output_file);

    if verbose {
        println!("Generated testbench contains:");
        println!("  Component: {}", testbench_data.component_name);
        println!(
            "  Template: {}",
            if matches.contains_id("template") {
                "Custom"
            } else {
                "Bundled default"
            }
        );
        if config.is_some() {
            println!("  Config: Applied");
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_stack_entity() {
        let vhdl_content = r#"
        library IEEE;
        use IEEE.std_logic_1164.all;
        entity stack is
          GENERIC (DATA_WIDTH : INTEGER := 32;
                   DEPTH      : INTEGER := 10);
          port (
            clk : in STD_LOGIC;
            rst : in STD_LOGIC;
            push : in STD_LOGIC;
            pop : in STD_LOGIC;
            data_in : in STD_LOGIC_VECTOR(DATA_WIDTH-1 downto 0);
            data_out : out STD_LOGIC_VECTOR(DATA_WIDTH-1 downto 0);
            empty : out STD_LOGIC;
            full : out STD_LOGIC
          );
        end entity stack;
        "#;

        let entity = VhdlParser::parse_content(vhdl_content).unwrap();

        assert_eq!(entity.name, "stack");
        assert_eq!(entity.generics.len(), 2);
        assert_eq!(entity.ports.len(), 8);

        // Check first generic
        assert_eq!(entity.generics[0].name, "data_width");
        assert_eq!(entity.generics[0].generic_type, "integer");
        assert_eq!(entity.generics[0].default_value, Some("32".to_string()));

        // Check first port
        assert_eq!(entity.ports[0].name, "clk");
        assert_eq!(entity.ports[0].direction, "in");
        assert_eq!(entity.ports[0].signal_type, "std_logic");

        // Check vector port with range
        let data_in_port = entity.ports.iter().find(|p| p.name == "data_in").unwrap();
        assert_eq!(
            data_in_port.range,
            Some("(DATA_WIDTH-1 downto 0)".to_string())
        );
    }

    #[test]
    fn test_testbench_generation() {
        let entity = VhdlEntity {
            name: "stack".to_string(),
            generics: vec![VhdlGeneric {
                name: "DATA_WIDTH".to_string(),
                generic_type: "INTEGER".to_string(),
                default_value: Some("32".to_string()),
            }],
            ports: vec![
                VhdlPort {
                    name: "clk".to_string(),
                    direction: "in".to_string(),
                    signal_type: "STD_LOGIC".to_string(),
                    range: None,
                },
                VhdlPort {
                    name: "data_in".to_string(),
                    direction: "in".to_string(),
                    signal_type: "STD_LOGIC_VECTOR".to_string(),
                    range: Some("(DATA_WIDTH-1 downto 0)".to_string()),
                },
                VhdlPort {
                    name: "data_out".to_string(),
                    direction: "out".to_string(),
                    signal_type: "STD_LOGIC_VECTOR".to_string(),
                    range: Some("(DATA_WIDTH-1 downto 0)".to_string()),
                },
            ],
        };

        let config = TestbenchConfig {
            clock_period_ns: Some(10),
            reset_duration_ns: Some(100),
            generics: Some(HashMap::from([(
                "DATA_WIDTH".to_string(),
                "32".to_string(),
            )])),
            test_vectors: None,
        };

        let testbench_data = TestbenchGenerator::generate_testbench_data(&entity, Some(&config));

        // Check that ranges are resolved
        assert!(testbench_data.ports.contains("(31 downto 0)"));
        assert!(testbench_data.internal_signals.contains("(31 downto 0)"));
    }
}
