#!/usr/bin/env python3
"""
Test script to verify UI logging is working correctly.
Run this to test the models generator output in the Textual UI.
"""
import asyncio
from pathlib import Path
import sys
import io

async def test_ui_logging():
    """Test if the run_python_script method shows output in the UI."""
    from main import CommandRunnerApp
    
    # Create app instance
    app = CommandRunnerApp()
    
    # Store logs that would be written
    logs = []
    original_write = app.write_ui_log
    
    def capture_log(msg):
        logs.append(msg)
        original_write(msg)
    
    app.write_ui_log = capture_log
    
    # Test the run_python_script method
    print("Starting async test of run_python_script...")
    print("Running: python -m lmarena.generator lmarena_models.txt\n")
    
    # Simulate running the generator
    await app.run_python_script(["-m", "lmarena.generator", "lmarena_models.txt"], "Test")
    
    # Print collected logs
    print(f"\nTotal logs captured: {len(logs)}")
    print("\nFirst 10 logs:")
    for i, log in enumerate(logs[:10]):
        safe_log = log[:80].encode('utf-8', errors='replace').decode('utf-8')
        print(f"  {i+1}. {safe_log}...")
    
    # Check if we got output
    found_models = any("Encontrados" in log for log in logs)
    found_process = any("Processo finalizado" in log for log in logs)
    
    print(f"\nFound 'Encontrados' message: {found_models}")
    print(f"Found 'Processo finalizado' message: {found_process}")
    
    if found_models and found_process:
        print("\n[SUCCESS] UI logging is working correctly!")
        return True
    else:
        print("\n[ERROR] UI logging may not be working properly")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_ui_logging())
    exit(0 if result else 1)

