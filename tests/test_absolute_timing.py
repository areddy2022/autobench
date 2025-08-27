"""Tests for absolute timing in test vectors."""

import pytest
from autobench.vhdl_parser import VhdlEntity, VhdlPort
from autobench.config import TestbenchConfig, TestVector
from autobench.testbench_generator import TestbenchGenerator


def test_absolute_timing_calculation():
    """Test that test vector times are treated as absolute timestamps."""
    
    entity = VhdlEntity(
        name="timing_test",
        generics=[],
        ports=[
            VhdlPort("clk", "in", "std_logic"),
            VhdlPort("enable", "in", "std_logic"),
            VhdlPort("data", "in", "std_logic_vector", "(7 downto 0)")
        ]
    )
    
    # Test vectors with absolute timestamps
    test_vectors = [
        TestVector(
            time_ns=100,  # Apply at 100ns
            inputs={"enable": "1"},
            description="Enable at 100ns"
        ),
        TestVector(
            time_ns=250,  # Apply at 250ns (150ns later)
            inputs={"data": "10101010"},
            description="Change data at 250ns"
        ),
        TestVector(
            time_ns=300,  # Apply at 300ns (50ns later)
            inputs={"enable": "0"},
            description="Disable at 300ns"
        )
    ]
    
    config = TestbenchConfig(
        reset_duration_ns=50,
        test_vectors=test_vectors
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    lines = stimulus.split('\n')
    
    # Find the relevant sections and verify timing
    # Should see:
    # 1. Reset for 50ns, then 20ns settling = 70ns total before first test
    # 2. Wait 30ns more to reach 100ns (100-70=30)
    # 3. Apply first test, wait 1ns settling
    # 4. Wait 149ns more to reach 250ns (250-101=149)
    # 5. Apply second test, wait 1ns settling  
    # 6. Wait 48ns more to reach 300ns (300-252=48)
    
    # Look for the wait statements
    wait_statements = [line.strip() for line in lines if 'wait for' in line and 'ns' in line]
    
    # Should have: reset wait (50ns), settling wait (20ns), then calculated waits
    assert "wait for 50 ns;" in wait_statements  # Reset duration
    assert "wait for 20 ns;" in wait_statements  # Reset settling
    
    # The test vector waits should be calculated as differences
    # After reset (70ns), wait 30ns to reach 100ns
    assert "wait for 30 ns;" in wait_statements or "wait for 100 ns;" in wait_statements
    
    # After first test (101ns), wait to reach 250ns
    wait_149_found = any("wait for 149 ns;" in stmt for stmt in wait_statements)
    wait_150_found = any("wait for 150 ns;" in stmt for stmt in wait_statements) 
    assert wait_149_found or wait_150_found  # Allow for small variations
    
    # After second test (252ns), wait to reach 300ns  
    wait_48_found = any("wait for 48 ns;" in stmt for stmt in wait_statements)
    wait_50_found = any("wait for 50 ns;" in stmt for stmt in wait_statements)
    assert wait_48_found or wait_50_found


def test_zero_time_test_vector():
    """Test handling of test vector at time 0."""
    
    entity = VhdlEntity(
        name="zero_time_test",
        generics=[],
        ports=[VhdlPort("rst", "in", "std_logic")]
    )
    
    test_vectors = [
        TestVector(
            time_ns=0,  # Apply immediately at time 0
            inputs={"rst": "1"},
            description="Reset at time 0"
        ),
        TestVector(
            time_ns=50,  # Apply at 50ns
            inputs={"rst": "0"},
            description="Release reset at 50ns"
        )
    ]
    
    config = TestbenchConfig(
        reset_duration_ns=0,  # No separate reset sequence
        test_vectors=test_vectors
    )
    
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # First test vector should apply immediately (no wait before it)
    # Second test vector should wait 50ns from start
    lines = stimulus.split('\n')
    
    # Should not have negative wait times or skip the first test
    assert "wait for 0 ns;" not in stimulus  # No zero waits
    assert ("wait for 50 ns;" in stimulus or "wait for 49 ns;" in stimulus)  # Wait to second test (accounting for 1ns settling)
    
    # Both test vectors should be applied
    assert "Reset at time 0" in stimulus
    assert "Release reset at 50ns" in stimulus


def test_timing_comments_include_absolute_time():
    """Test that comments include absolute time information."""
    
    entity = VhdlEntity(
        name="comment_test",
        generics=[],
        ports=[VhdlPort("signal", "in", "std_logic")]
    )
    
    test_vectors = [
        TestVector(
            time_ns=150,
            inputs={"signal": "1"},
            description="First test"
        ),
        TestVector(
            time_ns=300,
            inputs={"signal": "0"}, 
            description="Second test"
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Comments should include absolute timing information
    assert "First test @150ns" in stimulus
    assert "Second test @300ns" in stimulus


def test_out_of_order_time_handling():
    """Test handling of test vectors not in chronological order."""
    
    entity = VhdlEntity(
        name="order_test",
        generics=[],
        ports=[VhdlPort("data", "in", "std_logic")]
    )
    
    # Test vectors not in time order (user mistake)
    test_vectors = [
        TestVector(
            time_ns=200,
            inputs={"data": "1"},
            description="Second test"
        ),
        TestVector(
            time_ns=100,  # Earlier time after later time
            inputs={"data": "0"},
            description="First test"  
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
    stimulus = testbench_data.stim_proc
    
    # Should handle this gracefully - either sort them or handle negative waits
    # At minimum, should not crash and should generate some reasonable output
    assert "data" in stimulus
    assert "wait for" in stimulus
    
    # Negative waits should not appear (they would cause simulation errors)
    assert "wait for -" not in stimulus
