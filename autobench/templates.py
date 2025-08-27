"""Template handling for VHDL generation."""

from pathlib import Path
from typing import Optional

# Default template bundled into the module
DEFAULT_TEMPLATE = """--=============================================================================
--Library Declarations:
--=============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
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
component {component_name} is{generics}
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
uut: {component_name}{generic_map}
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
end testbench;"""


def generate_vhdl_template(entity_name: str) -> str:
    """Generate a VHDL entity template."""
    return f"""-- =============================================================================
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
"""


def save_vhdl_template(entity_name: str, path: Path) -> None:
    """Save VHDL template to file."""
    template_content = generate_vhdl_template(entity_name)
    try:
        path.write_text(template_content, encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to write VHDL template file '{path}': {e}")


def load_template(template_path: Optional[Path] = None) -> str:
    """Load template from file or return default template."""
    if template_path:
        try:
            return template_path.read_text(encoding='utf-8')
        except Exception as e:
            raise RuntimeError(f"Failed to read template file '{template_path}': {e}")
    else:
        return DEFAULT_TEMPLATE
