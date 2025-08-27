"""GHDL simulation runner for VHDL testbenches."""

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TestResult:
    """Represents the result of a single test assertion."""
    test_name: str
    passed: bool
    message: str
    time: Optional[str] = None
    severity: str = "error"


@dataclass 
class SimulationResult:
    """Complete simulation results."""
    success: bool
    compilation_output: str
    simulation_output: str
    test_results: List[TestResult]
    waveform_file: Optional[Path] = None
    errors: List[str] = None


class GHDLRunner:
    """Handles GHDL compilation and simulation of VHDL testbenches."""
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize GHDL runner."""
        self.work_dir = work_dir or Path.cwd()
        self.work_dir.mkdir(exist_ok=True)
    
    def check_ghdl_available(self) -> bool:
        """Check if GHDL is available on the system."""
        try:
            result = subprocess.run(
                ["ghdl", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def compile_and_simulate(
        self, 
        entity_file: Path, 
        testbench_file: Path,
        entity_name: str,
        testbench_name: str,
        generate_waveform: bool = True,
        simulation_time: Optional[str] = None
    ) -> SimulationResult:
        """Compile VHDL files and run simulation."""
        
        if not self.check_ghdl_available():
            return SimulationResult(
                success=False,
                compilation_output="",
                simulation_output="", 
                test_results=[],
                errors=["GHDL is not available. Please install GHDL first."]
            )
        
        try:
            # Step 1: Analyze (compile) the entity file
            entity_result = self._analyze_file(entity_file)
            if entity_result.returncode != 0:
                return SimulationResult(
                    success=False,
                    compilation_output=entity_result.stderr,
                    simulation_output="",
                    test_results=[],
                    errors=[f"Failed to compile entity: {entity_result.stderr}"]
                )
            
            # Step 2: Analyze (compile) the testbench file  
            tb_result = self._analyze_file(testbench_file)
            if tb_result.returncode != 0:
                return SimulationResult(
                    success=False,
                    compilation_output=f"{entity_result.stderr}\n{tb_result.stderr}",
                    simulation_output="",
                    test_results=[],
                    errors=[f"Failed to compile testbench: {tb_result.stderr}"]
                )
            
            # Step 3: Elaborate (link) the testbench
            elab_result = self._elaborate(testbench_name)
            if elab_result.returncode != 0:
                return SimulationResult(
                    success=False,
                    compilation_output=f"{entity_result.stderr}\n{tb_result.stderr}\n{elab_result.stderr}",
                    simulation_output="",
                    test_results=[],
                    errors=[f"Failed to elaborate: {elab_result.stderr}"]
                )
            
            # Step 4: Run simulation
            sim_result = self._run_simulation(
                testbench_name, 
                generate_waveform, 
                simulation_time
            )
            
            # Parse simulation output for test results
            test_results = self._parse_test_results(sim_result.stdout + sim_result.stderr)
            
            waveform_file = None
            if generate_waveform:
                waveform_file = self.work_dir / f"{testbench_name}.ghw"
                if not waveform_file.exists():
                    waveform_file = None
            
            return SimulationResult(
                success=sim_result.returncode == 0,
                compilation_output=f"{entity_result.stderr}\n{tb_result.stderr}\n{elab_result.stderr}",
                simulation_output=sim_result.stdout + sim_result.stderr,
                test_results=test_results,
                waveform_file=waveform_file,
                errors=[] if sim_result.returncode == 0 else [sim_result.stderr]
            )
            
        except Exception as e:
            return SimulationResult(
                success=False,
                compilation_output="",
                simulation_output="",
                test_results=[],
                errors=[f"Simulation failed: {e}"]
            )
    
    def _analyze_file(self, vhdl_file: Path) -> subprocess.CompletedProcess:
        """Analyze (compile) a VHDL file with GHDL."""
        return subprocess.run(
            ["ghdl", "-a", "--std=08", str(vhdl_file)],
            cwd=self.work_dir,
            capture_output=True,
            text=True
        )
    
    def _elaborate(self, entity_name: str) -> subprocess.CompletedProcess:
        """Elaborate (link) the design with GHDL."""
        return subprocess.run(
            ["ghdl", "-e", "--std=08", entity_name],
            cwd=self.work_dir,
            capture_output=True,
            text=True
        )
    
    def _run_simulation(
        self, 
        entity_name: str, 
        generate_waveform: bool = True,
        simulation_time: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Run the simulation with GHDL."""
        cmd = ["ghdl", "-r", "--std=08", entity_name]
        
        if generate_waveform:
            waveform_file = self.work_dir / f"{entity_name}.ghw"
            cmd.extend(["--wave=" + str(waveform_file)])
        
        if simulation_time:
            cmd.extend([f"--stop-time={simulation_time}"])
        else:
            # Default to reasonable simulation time
            cmd.extend(["--stop-time=10us"])
        
        return subprocess.run(
            cmd,
            cwd=self.work_dir,
            capture_output=True,
            text=True
        )
    
    def _parse_test_results(self, output: str) -> List[TestResult]:
        """Parse GHDL output to extract test results from assertions."""
        test_results = []
        
        # Look for assertion messages
        # GHDL assertion format: "filename:line:col:@time:(assertion): message"
        assertion_pattern = r'(.+?):(\d+):(\d+):@(\d+\w+):\((\w+)\): (.+)'
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Look for assertion failures
            match = re.search(assertion_pattern, line)
            if match:
                filename, line_num, col, time, severity, message = match.groups()
                
                # Try to extract test name from message
                test_name = self._extract_test_name(message)
                
                # Assertions typically indicate failures, but we can check for specific patterns
                passed = self._is_passing_assertion(message, severity)
                
                test_results.append(TestResult(
                    test_name=test_name,
                    passed=passed,
                    message=message,
                    time=time,
                    severity=severity.lower()
                ))
            
            # Also look for simple assertion messages without full location info
            elif "assertion" in line.lower() and ("error" in line.lower() or "failure" in line.lower()):
                test_name = self._extract_test_name(line)
                test_results.append(TestResult(
                    test_name=test_name,
                    passed=False,
                    message=line,
                    severity="error"
                ))
        
        return test_results
    
    def _extract_test_name(self, message: str) -> str:
        """Extract test name from assertion message."""
        # Look for patterns like "Test 1:", "Test_case_name:", etc.
        test_patterns = [
            r'Test\s+(\d+)',
            r'Test\s+(\w+)',
            r'(\w+)\s+test',
            r'Testing\s+(\w+)'
        ]
        
        for pattern in test_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return f"Test {match.group(1)}"
        
        # Fallback: use first few words of message
        words = message.split()[:3]
        return " ".join(words) if words else "Unknown Test"
    
    def _is_passing_assertion(self, message: str, severity: str) -> bool:
        """Determine if an assertion represents a passing or failing test."""
        # Most assertions in VHDL represent failures
        # But some might be informational
        message_lower = message.lower()
        
        if severity.lower() in ["note", "info"]:
            return True
        
        if any(word in message_lower for word in ["pass", "success", "ok", "correct"]):
            return True
            
        return False  # Default to failure for error/warning/assertion severities
    
    def cleanup_work_files(self) -> None:
        """Clean up GHDL work files."""
        work_files = [
            "work-obj08.cf",
            "work-obj93.cf", 
            "work-obj87.cf",
            "e~*.o",
            "*.exe"  # Windows executables
        ]
        
        for pattern in work_files:
            for file in self.work_dir.glob(pattern):
                try:
                    file.unlink()
                except OSError:
                    pass  # Ignore errors


def run_ghdl_simulation(
    entity_file: Path,
    testbench_file: Path, 
    entity_name: str,
    testbench_name: str,
    work_dir: Optional[Path] = None,
    generate_waveform: bool = True,
    simulation_time: Optional[str] = None,
    cleanup: bool = True
) -> SimulationResult:
    """Convenience function to run GHDL simulation."""
    
    runner = GHDLRunner(work_dir)
    
    try:
        result = runner.compile_and_simulate(
            entity_file=entity_file,
            testbench_file=testbench_file,
            entity_name=entity_name,
            testbench_name=testbench_name,
            generate_waveform=generate_waveform,
            simulation_time=simulation_time
        )
        
        return result
        
    finally:
        if cleanup:
            runner.cleanup_work_files()
