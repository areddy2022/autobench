"""Tests for generic parameter handling in testbench generation."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort, VhdlGeneric
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_generate_generics_string():
    """Test generation of generics for component declaration."""
    
    generics = [
        VhdlGeneric("DATA_WIDTH", "INTEGER", "8"),
        VhdlGeneric("DEPTH", "INTEGER", "16")
    ]
    
    # Test with no config (use defaults)
    generics_str = TestbenchGenerator._generate_generics_string(generics, None)
    
    assert "DATA_WIDTH : INTEGER := 8" in generics_str
    assert "DEPTH : INTEGER := 16" in generics_str
    assert "Generic (" in generics_str  # Should include Generic clause wrapper
    
    # Test with config overrides
    config = TestbenchConfig(generics={"DATA_WIDTH": "16", "DEPTH": "32"})
    generics_str = TestbenchGenerator._generate_generics_string(generics, config)
    
    assert "DATA_WIDTH : INTEGER := 16" in generics_str  # Overridden
    assert "DEPTH : INTEGER := 32" in generics_str       # Overridden


def test_generate_generic_map():
    """Test generation of generic map for component instantiation."""
    
    generics = [
        VhdlGeneric("DATA_WIDTH", "INTEGER", "8"),
        VhdlGeneric("FIFO_DEPTH", "INTEGER", "16")
    ]
    
    # Test with config values
    config = TestbenchConfig(generics={"DATA_WIDTH": "32", "FIFO_DEPTH": "64"})
    generic_map = TestbenchGenerator._generate_generic_map(generics, config)
    
    assert "DATA_WIDTH => 32" in generic_map
    assert "FIFO_DEPTH => 64" in generic_map
    assert "generic map(" in generic_map  # Should include generic map clause wrapper


def test_testbench_with_generics():
    """Test complete testbench generation with generic parameters."""
    
    entity = VhdlEntity(
        name="parameterized_fifo",
        generics=[
            VhdlGeneric("DATA_WIDTH", "INTEGER", "8"),
            VhdlGeneric("DEPTH", "INTEGER", "16")
        ],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("rst", "in", "std_logic"),
            VhdlPort("data_in", "in", "std_logic_vector", "(DATA_WIDTH-1 downto 0)"),
            VhdlPort("data_out", "out", "std_logic_vector", "(DATA_WIDTH-1 downto 0)"),
            VhdlPort("full", "out", "std_logic"),
            VhdlPort("empty", "out", "std_logic")
        ]
    )
    
    # Config with custom generic values
    config = TestbenchConfig(
        generics={"DATA_WIDTH": "16", "DEPTH": "32"},
        test_vectors=[
            TestVector(
                time_ns=100,
                inputs={"rst": "1", "data_in": "1010101010101010"},
                expected_outputs={"empty": "1", "full": "0"}
            )
        ]
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    # Check generic declaration in component
    assert "DATA_WIDTH : INTEGER := 16" in testbench_data.generics
    assert "DEPTH : INTEGER := 32" in testbench_data.generics
    
    # Check generic mapping in instantiation  
    assert "DATA_WIDTH => 16" in testbench_data.generic_map
    assert "DEPTH => 32" in testbench_data.generic_map
    
    # Check that generic resolution works in port ranges
    assert "(16-1 downto 0)" in testbench_data.ports  # DATA_WIDTH=16, so shows as expression
    assert "(16-1 downto 0)" in testbench_data.internal_signals


def test_generics_in_template_application():
    """Test that generics are properly applied to template."""
    
    entity = VhdlEntity(
        name="test_entity",
        generics=[VhdlGeneric("WIDTH", "INTEGER", "8")],
        ports=[VhdlPort("data", "in", "std_logic_vector", "(WIDTH-1 downto 0)")]
    )
    
    config = TestbenchConfig(generics={"WIDTH": "16"})
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    # Simple template with generic placeholders
    template = """
component {component_name} is
    Generic (
{generics}
    );
    Port ({ports});
end component;

{component_name}_inst: {component_name}
    generic map(
{generic_map}
    )
    port map({port_connections});
"""
    
    result = testbench_data.apply_to_template(template)
    
    # Check that generic values are properly substituted
    assert "WIDTH : INTEGER := 16" in result
    assert "WIDTH => 16" in result
    assert "test_entity_inst: test_entity" in result


def test_no_generics_handling():
    """Test that entities without generics work correctly."""
    
    entity = VhdlEntity(
        name="simple_entity",
        generics=[],  # No generics
        ports=[VhdlPort("clk", "in", "std_logic")]
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, None)
    
    # Should generate empty strings for generic-related fields
    assert testbench_data.generics == ""
    assert testbench_data.generic_map == ""
    
    # Template should still work (empty sections)
    template = "Generic ({generics}) Port ({ports}) Map ({generic_map})"
    result = testbench_data.apply_to_template(template)
    
    assert "Generic () Port" in result  # Empty generics section
    assert "Map ()" in result           # Empty generic map


def test_generic_case_insensitive_matching():
    """Test that generic config matching is case insensitive."""
    
    generics = [
        VhdlGeneric("data_width", "INTEGER", "8"),  # lowercase in VHDL
        VhdlGeneric("BUFFER_DEPTH", "INTEGER", "16")  # uppercase in VHDL
    ]
    
    # Config with different case
    config = TestbenchConfig(generics={
        "DATA_WIDTH": "32",     # uppercase config for lowercase VHDL
        "buffer_depth": "64"    # lowercase config for uppercase VHDL
    })
    
    generic_map = TestbenchGenerator._generate_generic_map(generics, config)
    
    # Should find matches despite case differences
    assert "data_width => 32" in generic_map
    assert "BUFFER_DEPTH => 64" in generic_map
