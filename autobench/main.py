"""Main CLI entry point for autobench."""

import click
from pathlib import Path
from typing import Optional

from .vhdl_parser import VhdlParser
from .config import load_config, save_config, generate_baseline_config
from .testbench_generator import TestbenchGenerator
from .templates import load_template, save_vhdl_template
from .ai_integration import generate_ai_config
from .ghdl_runner import run_ghdl_simulation


@click.group(invoke_without_command=True)
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True, path_type=Path),
              help='Input VHDL file to parse')
@click.option('-o', '--output', type=click.Path(path_type=Path),
              help='Output testbench file (default: <entity_name>_tb.vhd)')
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True, path_type=Path),
              help='Optional TOML configuration file')
@click.option('-t', '--template', 'template_file', type=click.Path(exists=True, path_type=Path),
              help='Custom testbench template file')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-g', '--generate-config', is_flag=True,
              help='Generate a baseline TOML configuration file and exit')
@click.pass_context
def main(ctx, input_file: Optional[Path], output: Optional[Path], config_file: Optional[Path],
         template_file: Optional[Path], verbose: bool, generate_config: bool):
    """VHDL Testbench Generator - Generate VHDL testbenches from entity files."""
    
    # If no subcommand was invoked and no input file provided, show help
    if ctx.invoked_subcommand is None and not input_file:
        click.echo(ctx.get_help())
        return
    
    # If a subcommand was invoked, let it handle execution
    if ctx.invoked_subcommand is not None:
        return
    
    # Main generation logic
    if verbose:
        click.echo(f"Parsing VHDL file: {input_file}")
    
    try:
        # Parse VHDL file
        entity = VhdlParser.parse_file(input_file)
        
        if verbose:
            click.echo(f"Parsed entity: {entity.name}")
            click.echo(f"  Generics: {len(entity.generics)}")
            click.echo(f"  Ports: {len(entity.ports)}")
        
        # If generate-config flag is set, generate baseline config and exit
        if generate_config:
            baseline_config = generate_baseline_config(entity)
            config_filename = Path(f"{entity.name}_config.toml")
            
            save_config(baseline_config, config_filename)
            
            click.echo(f"Generated baseline configuration file: {config_filename}")
            if verbose:
                click.echo("Edit this file to customize your test vectors and parameters,")
                click.echo(f"then run the generator again with: -i {input_file} -c {config_filename}")
            return
        
        # Load optional config
        config = None
        if config_file:
            if verbose:
                click.echo(f"Loading config from: {config_file}")
            config = load_config(config_file)
        else:
            # Try to find a default config file
            default_config = Path(f"{entity.name}_config.toml")
            if default_config.exists():
                if verbose:
                    click.echo(f"Found default config: {default_config}")
                config = load_config(default_config)
        
        # Generate testbench data
        testbench_data = TestbenchGenerator.generate_testbench_data(entity, config)
        
        # Load template
        if template_file and verbose:
            click.echo(f"Loading custom template from: {template_file}")
        elif verbose:
            click.echo("Using bundled default template")
        
        template = load_template(template_file)
        
        # Generate final testbench
        final_testbench = testbench_data.apply_to_template(template)
        
        # Determine output file
        if not output:
            output = Path(f"{entity.name}_tb.vhd")
        
        # Write to file
        output.write_text(final_testbench, encoding='utf-8')
        
        click.echo(f"Testbench generated successfully: {output}")
        
        if verbose:
            click.echo("Generated testbench contains:")
            click.echo(f"  Component: {testbench_data.component_name}")
            click.echo(f"  Template: {'Custom' if template_file else 'Bundled default'}")
            if config:
                click.echo("  Config: Applied")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        return 1


@main.command()
@click.argument('entity_name')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def generate_template(entity_name: str, verbose: bool):
    """Generate a VHDL entity template with the specified name."""
    template_filename = Path(f"{entity_name}.vhd")
    
    try:
        save_vhdl_template(entity_name, template_filename)
        
        click.echo(f"Generated VHDL template file: {template_filename}")
        if verbose:
            click.echo("Edit this file to implement your VHDL entity.")
            click.echo(f"After implementation, generate config with: autobench -i {template_filename} -g")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        return 1


@main.command()
@click.argument('vhdl_file', type=click.Path(exists=True, path_type=Path))
@click.option('-o', '--output', type=click.Path(path_type=Path),
              help='Output config file (default: <entity_name>_ai_config.toml)')
@click.option('-p', '--prompt', help='Additional prompt/requirements for AI')
@click.option('--project-id', help='Google Cloud project ID (or set GOOGLE_CLOUD_PROJECT env var)')
@click.option('--location', default='us-central1', help='Google Cloud location (default: us-central1)')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def generate_ai_config_cmd(vhdl_file: Path, output: Optional[Path], prompt: Optional[str], 
                          project_id: Optional[str], location: str, verbose: bool):
    """Generate intelligent testbench configuration using AI (Vertex AI)."""
    
    try:
        if verbose:
            click.echo(f"Using Vertex AI to generate configuration for: {vhdl_file}")
            if prompt:
                click.echo(f"Additional requirements: {prompt}")
        
        output_path = generate_ai_config(
            vhdl_file=vhdl_file,
            output_path=output,
            additional_prompt=prompt,
            project_id=project_id,
            location=location,
            verbose=verbose
        )
        
        click.echo(f"AI-generated configuration saved to: {output_path}")
        if verbose:
            click.echo("Review and edit the configuration as needed, then generate testbench with:")
            click.echo(f"autobench -i {vhdl_file} -c {output_path}")
    
    except ValueError as e:
        if "project ID" in str(e):
            click.echo("Error: Google Cloud project ID required.", err=True)
            click.echo("Set the GOOGLE_CLOUD_PROJECT environment variable or use --project-id option.", err=True)
            click.echo("Ensure you have authenticated with: gcloud auth application-default login", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        return 1
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        return 1


@main.command()
@click.argument('entity_file', type=click.Path(exists=True, path_type=Path))
@click.argument('testbench_file', type=click.Path(exists=True, path_type=Path))
@click.option('--entity-name', help='Entity name (auto-detected if not provided)')
@click.option('--testbench-name', help='Testbench entity name (auto-detected if not provided)')
@click.option('--work-dir', type=click.Path(path_type=Path), help='Working directory for GHDL files')
@click.option('--no-waveform', is_flag=True, help='Skip waveform generation (.ghw file)')
@click.option('--sim-time', help='Simulation time (e.g., "1us", "100ns")')
@click.option('--no-cleanup', is_flag=True, help='Keep GHDL work files after simulation')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
def simulate(entity_file: Path, testbench_file: Path, entity_name: Optional[str], 
            testbench_name: Optional[str], work_dir: Optional[Path], no_waveform: bool,
            sim_time: Optional[str], no_cleanup: bool, verbose: bool):
    """Run GHDL simulation of VHDL entity and testbench."""
    
    try:
        # Auto-detect entity names if not provided
        if not entity_name:
            if verbose:
                click.echo(f"Auto-detecting entity name from {entity_file}")
            try:
                entity = VhdlParser.parse_file(entity_file)
                entity_name = entity.name
            except Exception as e:
                click.echo(f"Error: Could not auto-detect entity name: {e}", err=True)
                return 1
        
        if not testbench_name:
            if verbose:
                click.echo(f"Auto-detecting testbench name from {testbench_file}")
            try:
                testbench_entity = VhdlParser.parse_file(testbench_file)
                testbench_name = testbench_entity.name
            except Exception as e:
                click.echo(f"Error: Could not auto-detect testbench name: {e}", err=True)
                return 1
        
        if verbose:
            click.echo(f"Entity: {entity_name}")
            click.echo(f"Testbench: {testbench_name}")
            click.echo(f"Generating waveform: {not no_waveform}")
            if sim_time:
                click.echo(f"Simulation time: {sim_time}")
        
        # Run simulation
        result = run_ghdl_simulation(
            entity_file=entity_file,
            testbench_file=testbench_file,
            entity_name=entity_name,
            testbench_name=testbench_name,
            work_dir=work_dir,
            generate_waveform=not no_waveform,
            simulation_time=sim_time,
            cleanup=not no_cleanup
        )
        
        # Report results
        if result.success:
            click.echo(f"✅ Simulation completed successfully")
            
            # Show test results
            if result.test_results:
                passed_tests = sum(1 for t in result.test_results if t.passed)
                total_tests = len(result.test_results)
                
                click.echo(f"\n📊 Test Results: {passed_tests}/{total_tests} passed")
                
                for test in result.test_results:
                    status = "✅ PASS" if test.passed else "❌ FAIL"
                    time_info = f" @{test.time}" if test.time else ""
                    click.echo(f"  {status}: {test.test_name}{time_info}")
                    if not test.passed and verbose:
                        click.echo(f"    💬 {test.message}")
                
                if passed_tests < total_tests:
                    click.echo(f"\n❌ {total_tests - passed_tests} test(s) failed")
            
            # Show waveform info
            if result.waveform_file:
                click.echo(f"\n🌊 Waveform saved: {result.waveform_file}")
                click.echo(f"   Open with: gtkwave {result.waveform_file}")
            
        else:
            click.echo("❌ Simulation failed", err=True)
            
            if result.errors:
                for error in result.errors:
                    click.echo(f"Error: {error}", err=True)
            
            if verbose and result.compilation_output:
                click.echo(f"\nCompilation output:\n{result.compilation_output}")
            
            if verbose and result.simulation_output:
                click.echo(f"\nSimulation output:\n{result.simulation_output}")
            
            return 1
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        return 1


if __name__ == "__main__":
    main()
