"""Gerador de estrutura de modelos do LMArena (módulo)."""
from __future__ import annotations
import json
import re
import sys
from typing import Any, List, Dict, TextIO, Optional


class ModelsGenerator:
    @staticmethod
    def extract_initial_models(raw_data: str, output_stream: Optional[TextIO] = None) -> List[Dict[str, Any]]:
        models = []
        if "initialModels" in raw_data:
            try:
                # Primeiro tenta extrair usando regex para encontrar o array JSON
                m = re.search(r'initialModels\s*:\s*(\[[\s\S]*?\])', raw_data, re.DOTALL)
                if m:
                    json_str = m.group(1)
                else:
                    # Fallback: antiga heurística (caso específico)
                    start = raw_data.find("initialModels")
                    end = raw_data.find("initialModelAId", start)
                    if start != -1 and end != -1:
                        json_str = raw_data[start + len("initialModels"):end]
                        json_str = re.sub(r'^[^[]*', '', json_str)
                        json_str = re.sub(r'[^\]]*$', '', json_str)
                    else:
                        # Se não encontramos um fim claro, tentamos extrair desde a primeira '[' depois de 'initialModels' até o primeiro ']' seguinte
                        start_bracket = raw_data.find('[', start)
                        if start_bracket != -1:
                            end_bracket = raw_data.find(']', start_bracket)
                            if end_bracket != -1:
                                json_str = raw_data[start_bracket:end_bracket+1]
                            else:
                                json_str = None
                        else:
                            json_str = None

                if json_str:
                    try:
                        models = json.loads(json_str)
                    except json.JSONDecodeError:
                        try:
                            json_str_decoded = bytes(json_str, "utf-8").decode("unicode_escape")
                            models = json.loads(json_str_decoded)
                        except Exception as e:
                            msg = f"Erro ao fazer parse do JSON após unicode_escape: {e}\n"
                            if output_stream:
                                output_stream.write(msg)
                                output_stream.flush()
                            raise
                else:
                    # Não conseguimos extrair; será tratado abaixo pelo parse geral
                    models = []
            except Exception as e:
                msg = f"Erro ao fazer parse do JSON: {e}\n"
                if output_stream:
                    output_stream.write(msg)
                    output_stream.flush()
                if 'json_str' in locals() and json_str:
                    msg2 = f"String problemática (primeiros 200 chars):\n{json_str[:200]}\n"
                    if output_stream:
                        output_stream.write(msg2)
                        output_stream.flush()
        else:
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    models = data
                elif isinstance(data, dict) and 'initialModels' in data:
                    models = data['initialModels']
            except json.JSONDecodeError as e:
                msg = f"Erro ao fazer parse dos dados: {e}\n"
                if output_stream:
                    output_stream.write(msg)
                    output_stream.flush()
        return models

    @staticmethod
    def normalize_model(model: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            'id': model.get('id'),
            'publicName': model.get('publicName'),
            'capabilities': model.get('capabilities', {}),
        }
        if 'organization' in model:
            normalized['organization'] = model['organization']
        if 'provider' in model:
            normalized['provider'] = model['provider']
        if 'rank' in model:
            normalized['rank'] = model['rank']
        return normalized

    @staticmethod
    def format_models_python(models: List[Dict[str, Any]]) -> str:
        lines = ["models = ["]
        for i, model in enumerate(models):
            normalized = ModelsGenerator.normalize_model(model)
            model_str = "    {"
            fields = []
            if 'id' in normalized:
                fields.append(f"'id': {json.dumps(normalized['id'])}")
            if 'publicName' in normalized:
                fields.append(f"'publicName': {json.dumps(normalized['publicName'])}")
            if 'capabilities' in normalized:
                caps = normalized['capabilities']
                caps_str = ModelsGenerator._format_capabilities(caps)
                fields.append(f"'capabilities': {caps_str}")
            if 'organization' in normalized:
                fields.append(f"'organization': {json.dumps(normalized['organization'])}")
            if 'provider' in normalized:
                fields.append(f"'provider': {json.dumps(normalized['provider'])}")
            if 'rank' in normalized:
                fields.append(f"'rank': {normalized['rank']}")
            model_str += ", ".join(fields)
            model_str += "}"
            if i < len(models) - 1:
                model_str += ","
            lines.append(model_str)
        lines.append("]")
        return "\n".join(lines)

    @staticmethod
    def _format_capabilities(caps: Dict[str, Any]) -> str:
        return json.dumps(caps, ensure_ascii=False) \
            .replace('true', 'True') \
            .replace('false', 'False') \
            .replace('null', 'None')

    @staticmethod
    def extract_text_models(models: List[Dict[str, Any]]) -> Dict[str, str]:
        return {
            model["publicName"]: model["id"]
            for model in models
            if "text" in model.get("capabilities", {}).get("outputCapabilities", {})
        }

    @staticmethod
    def extract_image_models(models: List[Dict[str, Any]]) -> Dict[str, str]:
        return {
            model["publicName"]: model["id"]
            for model in models
            if "image" in model.get("capabilities", {}).get("outputCapabilities", {})
        }

    @staticmethod
    def extract_vision_models(models: List[Dict[str, Any]]) -> List[str]:
        return [
            model["publicName"]
            for model in models
            if "image" in model.get("capabilities", {}).get("inputCapabilities", {})
        ]

    @staticmethod
    def generate_full_code(models: List[Dict[str, Any]], output_stream: Optional[TextIO] = None) -> str:
        models_code = ModelsGenerator.format_models_python(models)
        text_models = ModelsGenerator.extract_text_models(models)
        image_models = ModelsGenerator.extract_image_models(models)
        vision_models = ModelsGenerator.extract_vision_models(models)
        text_models_code = f"text_models = {json.dumps(text_models, ensure_ascii=False)}"
        image_models_code = f"image_models = {json.dumps(image_models, ensure_ascii=False)}"
        vision_models_code = f"vision_models = {json.dumps(vision_models, ensure_ascii=False)}"
        code = f"""{models_code}

{text_models_code}

{image_models_code}

{vision_models_code}
"""
        return code


def main(output_stream: Optional[TextIO] = None):
    if output_stream is None:
        output_stream = sys.stdout
    
    if len(sys.argv) < 2:
        output_stream.write("Uso: python models_generator.py <arquivo_json_ou_texto>\n")
        output_stream.write("\nExemplo:\n")
        output_stream.write("  python models_generator.py dados_lmarena.json\n")
        output_stream.flush()
        sys.exit(1)
    input_file = sys.argv[1]
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = f.read()
    except FileNotFoundError:
        output_stream.write(f"Erro: Arquivo '{input_file}' não encontrado.\n")
        output_stream.flush()
        sys.exit(1)
    
    output_stream.write(f"Processando arquivo: {input_file}\n")
    output_stream.flush()
    
    models = ModelsGenerator.extract_initial_models(raw_data, output_stream)
    if not models:
        output_stream.write("Nenhum modelo encontrado nos dados.\n")
        output_stream.flush()
        sys.exit(1)
    
    output_stream.write(f"Encontrados {len(models)} modelos.\n")
    output_stream.flush()
    
    code = ModelsGenerator.generate_full_code(models, output_stream)
    output_stream.write(code)
    output_stream.write("\n")
    output_stream.flush()
    output_file = input_file.replace('.json', '_models.py').replace('.txt', '_models.py')
    if output_file != input_file:
        output_stream.write(f"\nSalvando código em: {output_file}\n")
        output_stream.flush()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(code)
        output_stream.write(f"Código salvo com sucesso em: {output_file}\n")
        output_stream.flush()


def example_extract_and_save_json():
    # Apenas um exemplo curto; o original tem um payload muito longo.
    sys.stdout.write("Exemplo de extração (skip) - use CLI com arquivo real\n")
    sys.stdout.flush()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        example_extract_and_save_json()
    else:
        main()
