"""Tests for testbench generator."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlGeneric, VhdlPort
from autobench.config import TestbenchConfig
from autobench.testbench_generator import TestbenchGenerator


def test_testbench_generation():
    """Test basic testbench generation."""
    entity = VhdlEntity(
        name="stack",
        generics=[VhdlGeneric(
            name="DATA_WIDTH",
            generic_type="INTEGER",
            default_value="32"
        )],
        ports=[
            VhdlPort(
                name="clk",
                direction="in",
                signal_type="STD_LOGIC",
                range=None
            ),
            VhdlPort(
                name="data_in",
                direction="in",
                signal_type="STD_LOGIC_VECTOR",
                range="(DATA_WIDTH-1 downto 0)"
            ),
            VhdlPort(
                name="data_out",
                direction="out",
                signal_type="STD_LOGIC_VECTOR",
                range="(DATA_WIDTH-1 downto 0)"
            )
        ]
    )
    
    config = TestbenchConfig(
        clock_period_ns=10,
        reset_duration_ns=100,
        generics={"DATA_WIDTH": "32"}
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    # Check that ranges are resolved (the parser converts generic names to lowercase)
    assert "(32-1 downto 0)" in testbench_data.ports
    assert "(32-1 downto 0)" in testbench_data.internal_signals
    assert testbench_data.component_name == "stack"


def test_clock_generation():
    """Test clock generation with different periods."""
    entity = VhdlEntity(name="test", generics=[], ports=[])
    
    config = TestbenchConfig(clock_period_ns=20)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    assert "wait for 10 ns" in testbench_data.clk_gen


def test_port_connections():
    """Test port map generation."""
    ports = [
        VhdlPort("clk", "in", "STD_LOGIC"),
        VhdlPort("data", "out", "STD_LOGIC_VECTOR", "(7 downto 0)")
    ]
    
    entity = VhdlEntity(name="test", generics=[], ports=ports)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity)
    
    assert "clk => tb_clk," in testbench_data.port_connections
    assert "data => tb_data" in testbench_data.port_connections
