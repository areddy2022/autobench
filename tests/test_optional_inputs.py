"""Test handling of test vectors with optional inputs."""

import pytest
from autobench.config import TestbenchConfig, TestVector


def test_test_vector_with_no_inputs():
    """Test test vector that only has expected outputs."""
    
    # TOML data representing test vectors where some only have outputs
    toml_data = {
        'clock_period_ns': 10,
        'test_vectors': [
            {
                'time_ns': 100,
                'description': 'Test with inputs and outputs',
                'inputs': {'enable': '1', 'data': '10101010'},
                'expected_outputs': {'ready': '1'}
            },
            {
                'time_ns': 200, 
                'description': 'Test with only outputs (no inputs change)',
                # No 'inputs' key at all
                'expected_outputs': {'ready': '0', 'count': '5'}
            },
            {
                'time_ns': 300,
                'description': 'Test with only inputs (no expected outputs)',
                'inputs': {'enable': '0'},
                # No 'expected_outputs'
            }
        ]
    }
    
    # This should not raise an exception
    config = TestbenchConfig.from_dict(toml_data)
    
    assert len(config.test_vectors) == 3
    
    # First vector has both inputs and outputs
    assert config.test_vectors[0].inputs == {'enable': '1', 'data': '10101010'}
    assert config.test_vectors[0].expected_outputs == {'ready': '1'}
    
    # Second vector has no inputs (should be empty dict)
    assert config.test_vectors[1].inputs == {}
    assert config.test_vectors[1].expected_outputs == {'ready': '0', 'count': '5'}
    
    # Third vector has no expected outputs (should be None)
    assert config.test_vectors[2].inputs == {'enable': '0'}
    assert config.test_vectors[2].expected_outputs is None


def test_test_vector_serialization_with_empty_inputs():
    """Test that test vectors with empty inputs serialize correctly."""
    
    test_vectors = [
        TestVector(
            time_ns=100,
            inputs={'enable': '1'},
            expected_outputs={'ready': '1'},
            description='Normal test'
        ),
        TestVector(
            time_ns=200,
            inputs={},  # Empty inputs
            expected_outputs={'ready': '0'},
            description='Only outputs test'
        )
    ]
    
    config = TestbenchConfig(test_vectors=test_vectors)
    
    # Should serialize without error
    config_dict = config.to_dict()
    
    assert len(config_dict['test_vectors']) == 2
    assert config_dict['test_vectors'][0]['inputs'] == {'enable': '1'}
    assert config_dict['test_vectors'][1]['inputs'] == {}  # Empty but present


def test_round_trip_with_optional_sections():
    """Test complete round trip with optional inputs/outputs."""
    
    # Create config with mixed test vectors
    original_config = TestbenchConfig(
        clock_period_ns=10,
        test_vectors=[
            TestVector(
                time_ns=50,
                inputs={'rst': '1'},
                expected_outputs={'ready': '0'},
                description='Reset test'
            ),
            TestVector(
                time_ns=100,
                inputs={},  # No inputs change
                expected_outputs={'ready': '1'},
                description='Wait for ready'
            )
        ]
    )
    
    # Convert to dict and back
    config_dict = original_config.to_dict()
    rebuilt_config = TestbenchConfig.from_dict(config_dict)
    
    # Should be identical
    assert rebuilt_config.clock_period_ns == original_config.clock_period_ns
    assert len(rebuilt_config.test_vectors) == len(original_config.test_vectors)
    
    assert rebuilt_config.test_vectors[0].inputs == {'rst': '1'}
    assert rebuilt_config.test_vectors[1].inputs == {}
