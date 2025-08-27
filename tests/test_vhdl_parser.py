"""Tests for VHDL parser."""

import pytest
from autobench.vhdl_parser import VhdlParser, VhdlEntity, VhdlGeneric, VhdlPort


def test_parse_stack_entity():
    """Test parsing a stack entity."""
    vhdl_content = """
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
    """
    
    entity = VhdlParser.parse_content(vhdl_content)
    
    assert entity.name == "stack"
    assert len(entity.generics) == 2
    assert len(entity.ports) == 8
    
    # Check first generic
    assert entity.generics[0].name == "data_width"
    assert entity.generics[0].generic_type == "integer"
    assert entity.generics[0].default_value == "32"
    
    # Check first port
    assert entity.ports[0].name == "clk"
    assert entity.ports[0].direction == "in"
    assert entity.ports[0].signal_type == "std_logic"
    
    # Check vector port with range
    data_in_port = next(p for p in entity.ports if p.name == "data_in")
    assert data_in_port.range == "(data_width-1 downto 0)"


def test_simple_entity():
    """Test parsing a simple entity without generics."""
    vhdl_content = """
    entity counter is
        port (
            clk : in std_logic;
            enable : in std_logic;
            count : out integer
        );
    end entity;
    """
    
    entity = VhdlParser.parse_content(vhdl_content)
    
    assert entity.name == "counter"
    assert len(entity.generics) == 0
    assert len(entity.ports) == 3


def test_entity_with_comments():
    """Test parsing entity with comments."""
    vhdl_content = """
    -- This is a comment
    entity test is
        -- Another comment
        port (
            clk : in std_logic; -- Clock signal
            data : out std_logic_vector(7 downto 0) -- Data output
        );
    end entity;
    """
    
    entity = VhdlParser.parse_content(vhdl_content)
    
    assert entity.name == "test"
    assert len(entity.ports) == 2
    assert entity.ports[1].range == "(7 downto 0)"


def test_missing_entity_error():
    """Test error when entity is not found."""
    vhdl_content = """
    library IEEE;
    use IEEE.std_logic_1164.all;
    -- No entity here
    """
    
    with pytest.raises(ValueError, match="Could not find entity name"):
        VhdlParser.parse_content(vhdl_content)
