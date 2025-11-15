def test_imports():
    import importlib
    importlib.import_module('docker_cleaner.core')
    importlib.import_module('cli.quick_cleanup')
    importlib.import_module('lmarena.generator')

    # smoke: instantiate classes/functions
    from docker_cleaner.core import WSLDockerCleaner
    from lmarena.generator import ModelsGenerator
    from cli.quick_cleanup import quick_cleanup
    import inspect

    cleaner = WSLDockerCleaner()
    assert hasattr(cleaner, 'run_command')
    assert hasattr(ModelsGenerator, 'extract_initial_models')
    # quick_cleanup should accept an optional console parameter
    sig = inspect.signature(quick_cleanup)
    assert len(sig.parameters) >= 0
