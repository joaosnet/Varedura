import io
import json
import sys
import pytest
import os
from lmarena.generator import ModelsGenerator


def test_normalize_and_format():
    models = [
        {
            "id": "m1",
            "publicName": "Model One",
            "capabilities": {"outputCapabilities": {"text": True}},
            "organization": "org",
            "provider": "prov",
            "rank": 10,
        }
    ]
    normalized = ModelsGenerator.normalize_model(models[0])
    assert normalized["id"] == "m1"
    assert normalized["organization"] == "org"

    py_code = ModelsGenerator.format_models_python(models)
    assert "models = [" in py_code
    assert "'id': \"m1\"" in py_code
    # capabilities should be present
    assert "capabilities" in py_code


def test_extract_text_image_vision_and_full_code():
    models = [
        {"id": "m1", "publicName": "TextModel", "capabilities": {"outputCapabilities": {"text": True}}},
        {"id": "m2", "publicName": "ImageModel", "capabilities": {"outputCapabilities": {"image": True}, "inputCapabilities": {"image": True}}}
    ]
    text_models = ModelsGenerator.extract_text_models(models)
    assert "TextModel" in text_models and text_models["TextModel"] == "m1"
    image_models = ModelsGenerator.extract_image_models(models)
    assert "ImageModel" in image_models and image_models["ImageModel"] == "m2"
    vision = ModelsGenerator.extract_vision_models(models)
    assert "ImageModel" in vision

    code = ModelsGenerator.generate_full_code(models)
    assert "text_models =" in code
    assert "image_models =" in code
    assert "vision_models =" in code


def test_extract_initial_models_regex_and_invalid_json_stream():
    # Embedded JSON array in arbitrary text
    raw = "prefix initialModels: [ {\"id\": \"r1\", \"publicName\": \"X\"} ] suffix"
    models = ModelsGenerator.extract_initial_models(raw)
    assert isinstance(models, list) and len(models) == 1

    # Invalid JSON - expect JSON decode to raise and be reported to output stream
    invalid_raw = "initialModels: [ { 'id': 'bad', } ]"
    stream = io.StringIO()
    try:
        ModelsGenerator.extract_initial_models(invalid_raw, output_stream=stream)
        # No exception thrown, but should not parse valid models
        assert [] == ModelsGenerator.extract_initial_models(invalid_raw)
    except Exception:
        # Extraction may raise; ensure we wrote diagnostic information
        content = stream.getvalue()
        assert "Erro ao" in content or "String problemática" in content


def test_main_usage_and_file_processing(tmp_path, monkeypatch):
    # Test usage (no args)
    monkeypatch.setattr(sys, "argv", ["generator.py"])
    out = io.StringIO()
    with pytest.raises(SystemExit):
        from lmarena import generator
        generator.main(output_stream=out)
    assert "Uso: python models_generator.py" in out.getvalue()

    # Test processing a JSON file
    models = [{"id": "a", "publicName": "A", "capabilities": {"outputCapabilities": {"text": True}}}]
    f = tmp_path / "in.json"
    f.write_text(json.dumps({"initialModels": models}))
    monkeypatch.setattr(sys, "argv", ["generator.py", str(f)])
    out2 = io.StringIO()
    from lmarena import generator
    generator.main(output_stream=out2)
    # a file with suffix _models.py should be created
    out_file = str(f).replace('.json', '_models.py')
    assert os.path.exists(out_file)
    assert "models = [" in out2.getvalue()


def test_extract_initial_models_from_json_dict_and_list():
    data_dict = {"initialModels": [{"id": "d1", "publicName": "D"}]}
    models = ModelsGenerator.extract_initial_models(json.dumps(data_dict))
    assert isinstance(models, list) and models[0]['id'] == 'd1'

    # Raw data is a direct list
    data_list = [{"id": "l1", "publicName": "L"}]
    models2 = ModelsGenerator.extract_initial_models(json.dumps(data_list))
    assert isinstance(models2, list) and models2[0]['id'] == 'l1'


def test_format_capabilities_conversion():
    caps = {"flag": True, "neg": False, "n": None}
    s = ModelsGenerator._format_capabilities(caps)
    assert 'True' in s and 'False' in s and 'None' in s
