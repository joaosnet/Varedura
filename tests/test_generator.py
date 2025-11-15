from lmarena.generator import ModelsGenerator


def test_extract_initial_models_simple():
    raw = '{"initialModels": [{"id": "1", "publicName": "a", "capabilities": {"inputCapabilities": {"text": true}, "outputCapabilities": {"text": true}}}]}'
    models = ModelsGenerator.extract_initial_models(raw)
    assert isinstance(models, list)
    assert len(models) == 1
    assert models[0]['id'] == '1'
