"""Tests for optimized test vector generation."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort, VhdlGeneric
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_optimized_test_vectors():
    """Test that only changed inputs are included in test vectors."""
    entity = VhdlEntity(
        name="counter",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("rst", "in", "std_logic"), 
            VhdlPort("enable", "in", "std_logic"),
            VhdlPort("data_in", "in", "std_logic_vector", "(7 downto 0)"),
            VhdlPort("count", "out", "integer")
        ]
    )
    
    # Create test vectors where only some inputs change
    test_vectors = [
        TestVector(
            time_ns=50,
            inputs={
                "enable": "'0'",
                "data_in": "\"00000000\""
            },
            description="Initialize inputs"
        ),
        TestVector(
            time_ns=100,
            inputs={
                "enable": "'1'"  # Only enable changes, data_in stays the same
            },
            description="Enable counter"
        ),
        TestVector(
            time_ns=150,
            inputs={
                "data_in": "\"11111111\""  # Only data_in changes, enable stays '1'
            },
            description="Change data input"
        )
    ]
    
    config = TestbenchConfig(
        clock_period_ns=10,
        reset_duration_ns=100,
        test_vectors=test_vectors
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    
    # Check that the stimulus process only includes signals that change
    stimulus = testbench_data.stim_proc
    
    # First test vector should have both signals
    assert "tb_enable <= '0';" in stimulus
    assert "tb_data_in <= \"00000000\";" in stimulus
    
    # Second test vector should only have enable (data_in unchanged)
    lines = stimulus.split('\n')
    test2_start = None
    test3_start = None
    
    for i, line in enumerate(lines):
        if "Test 2:" in line:
            test2_start = i
        elif "Test 3:" in line:
            test3_start = i
            break
    
    assert test2_start is not None, "Test 2 section not found"
    assert test3_start is not None, "Test 3 section not found"
    
    # Extract Test 2 section
    test2_section = '\n'.join(lines[test2_start:test3_start])
    
    # Test 2 should only change enable, not data_in
    assert "tb_enable <= '1';" in test2_section
    assert "tb_data_in <= \"00000000\";" not in test2_section  # Should not reassign unchanged signal
    
    # Extract Test 3 section  
    test3_section = '\n'.join(lines[test3_start:])
    
    # Test 3 should only change data_in, not enable
    assert "tb_data_in <= \"11111111\";" in test3_section
    assert "tb_enable <= '1';" not in test3_section  # Should not reassign unchanged signal


def test_complete_vs_optimized_vectors():
    """Compare complete vs optimized test vector approaches."""
    entity = VhdlEntity(
        name="simple",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("a", "in", "std_logic"),
            VhdlPort("b", "in", "std_logic"),
            VhdlPort("y", "out", "std_logic")
        ]
    )
    
    # Complete approach - all inputs in every vector
    complete_vectors = [
        TestVector(
            time_ns=50,
            inputs={"a": "'0'", "b": "'0'"},
            description="Both inputs low"
        ),
        TestVector(
            time_ns=100,
            inputs={"a": "'1'", "b": "'0'"},  # Repeats b even though unchanged
            description="A high, B low"
        )
    ]
    
    # Optimized approach - only changed inputs
    optimized_vectors = [
        TestVector(
            time_ns=50,
            inputs={"a": "'0'", "b": "'0'"},
            description="Both inputs low"
        ),
        TestVector(
            time_ns=100,
            inputs={"a": "'1'"},  # Only a changes
            description="A high, B stays low"
        )
    ]
    
    complete_config = TestbenchConfig(test_vectors=complete_vectors)
    optimized_config = TestbenchConfig(test_vectors=optimized_vectors)
    
    complete_data = TestbenchGenerator.generate_testbench_data(entity, complete_config)
    optimized_data = TestbenchGenerator.generate_testbench_data(entity, optimized_config)
    
    # Both should produce valid testbenches
    assert "tb_a <= '0';" in complete_data.stim_proc
    assert "tb_a <= '1';" in complete_data.stim_proc
    assert "tb_b <= '0';" in complete_data.stim_proc
    
    assert "tb_a <= '0';" in optimized_data.stim_proc
    assert "tb_a <= '1';" in optimized_data.stim_proc
    assert "tb_b <= '0';" in optimized_data.stim_proc
    
    # Optimized should be more concise (fewer signal assignments)
    complete_assignments = complete_data.stim_proc.count("<=")
    optimized_assignments = optimized_data.stim_proc.count("<=")
    
    assert optimized_assignments < complete_assignments, "Optimized version should have fewer signal assignments"
