"""
Gerador de estrutura de modelos a partir de dados brutos do LMArena.
Converte dados JSON em formato Python list of dicts.

Uso:
    # Como script de linha de comando
    python models_generator.py <arquivo_json_ou_texto>
    
    # Ver exemplos de uso
    python models_generator.py --examples
    
    # Como módulo
    from etc.tool.models_generator import ModelsGenerator
    
    models = ModelsGenerator.extract_initial_models(raw_data)
    text_models = ModelsGenerator.extract_text_models(models)
    code = ModelsGenerator.generate_full_code(models)
"""

import json
import re
from typing import Any, List, Dict
from rich import print


class ModelsGenerator:
    """Classe para processar e gerar estrutura de modelos."""
    
    @staticmethod
    def extract_initial_models(raw_data: str) -> List[Dict[str, Any]]:
        """
        Extrai a lista de modelos iniciais de dados brutos.
        
        Args:
            raw_data: String contendo os dados brutos do LMArena (pode ser JSON ou texto)
            
        Returns:
            Lista de dicionários representando os modelos
        """
        models = []
        
        # Tenta encontrar "initialModels" na string
        if "initialModels" in raw_data:
            try:
                # Extrai a parte entre "initialModels" e "initialModelAId"
                start = raw_data.find("initialModels")
                end = raw_data.find("initialModelAId", start)
                
                if start != -1 and end != -1:
                    # Extrai o JSON array
                    json_str = raw_data[start + len("initialModels"):end]
                    
                    # Remove tudo que não seja [ no início
                    json_str = re.sub(r'^[^[]*', '', json_str)
                    
                    # Remove tudo que não seja ] no final
                    json_str = re.sub(r'[^\]]*$', '', json_str)
                    
                    # Tenta fazer parse do JSON
                    try:
                        models = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Se falhar, tenta com unicode_escape
                        try:
                            json_str_decoded = bytes(json_str, "utf-8").decode("unicode_escape")
                            models = json.loads(json_str_decoded)
                        except Exception as e:
                            print(f"Erro ao fazer parse do JSON após unicode_escape: {e}")
                            raise
                    
            except Exception as e:
                print(f"Erro ao fazer parse do JSON: {e}")
                if 'json_str' in locals():
                    print(f"String problemática (primeiros 200 chars):\n{json_str[:200]}")
        else:
            # Se não encontrar "initialModels", tenta parse direto como JSON
            try:
                data = json.loads(raw_data)
                if isinstance(data, list):
                    models = data
                elif isinstance(data, dict) and 'initialModels' in data:
                    models = data['initialModels']
            except json.JSONDecodeError as e:
                print(f"Erro ao fazer parse dos dados: {e}")
        
        return models
    
    @staticmethod
    def normalize_model(model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza um modelo garantindo campos padrão.
        
        Args:
            model: Dicionário do modelo
            
        Returns:
            Modelo normalizado
        """
        normalized = {
            'id': model.get('id'),
            'publicName': model.get('publicName'),
            'capabilities': model.get('capabilities', {}),
        }
        
        # Adiciona organization e provider se existirem
        if 'organization' in model:
            normalized['organization'] = model['organization']
        if 'provider' in model:
            normalized['provider'] = model['provider']
        
        # Adiciona rank se existir
        if 'rank' in model:
            normalized['rank'] = model['rank']
        
        return normalized
    
    @staticmethod
    def format_models_python(models: List[Dict[str, Any]]) -> str:
        """
        Formata uma lista de modelos como código Python.
        
        Args:
            models: Lista de dicionários dos modelos
            
        Returns:
            String formatada como Python code
        """
        lines = ["models = ["]
        
        for i, model in enumerate(models):
            normalized = ModelsGenerator.normalize_model(model)
            
            # Formata o dicionário
            model_str = "    {"
            
            # Adiciona os campos na ordem: id, publicName, capabilities, organization, provider, rank
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
            
            # Junta os campos
            model_str += ", ".join(fields)
            model_str += "}"
            
            # Adiciona vírgula se não for o último
            if i < len(models) - 1:
                model_str += ","
            
            lines.append(model_str)
        
        lines.append("]")
        return "\n".join(lines)
    
    @staticmethod
    def _format_capabilities(caps: Dict[str, Any]) -> str:
        """
        Formata o dicionário de capabilities.
        
        Args:
            caps: Dicionário de capabilities
            
        Returns:
            String formatada
        """
        return json.dumps(caps, ensure_ascii=False) \
            .replace('true', 'True') \
            .replace('false', 'False') \
            .replace('null', 'None')
    
    @staticmethod
    def extract_text_models(models: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extrai modelos de texto (que têm 'text' em outputCapabilities).
        
        Args:
            models: Lista de modelos
            
        Returns:
            Dicionário {publicName: id} dos modelos de texto
        """
        return {
            model["publicName"]: model["id"]
            for model in models
            if "text" in model.get("capabilities", {}).get("outputCapabilities", {})
        }
    
    @staticmethod
    def extract_image_models(models: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extrai modelos de imagem (que têm 'image' em outputCapabilities).
        
        Args:
            models: Lista de modelos
            
        Returns:
            Dicionário {publicName: id} dos modelos de imagem
        """
        return {
            model["publicName"]: model["id"]
            for model in models
            if "image" in model.get("capabilities", {}).get("outputCapabilities", {})
        }
    
    @staticmethod
    def extract_vision_models(models: List[Dict[str, Any]]) -> List[str]:
        """
        Extrai modelos com visão (que têm 'image' em inputCapabilities).
        
        Args:
            models: Lista de modelos
            
        Returns:
            Lista de publicNames dos modelos com visão
        """
        return [
            model["publicName"]
            for model in models
            if "image" in model.get("capabilities", {}).get("inputCapabilities", {})
        ]
    
    @staticmethod
    def generate_full_code(models: List[Dict[str, Any]]) -> str:
        """
        Gera código Python completo com modelos e dicionários derivados.
        
        Args:
            models: Lista de modelos
            
        Returns:
            String com código Python completo
        """
        # Formata os modelos
        models_code = ModelsGenerator.format_models_python(models)
        
        # Extrai os dicionários derivados
        text_models = ModelsGenerator.extract_text_models(models)
        image_models = ModelsGenerator.extract_image_models(models)
        vision_models = ModelsGenerator.extract_vision_models(models)
        
        # Formata os dicionários
        text_models_code = f"text_models = {json.dumps(text_models, ensure_ascii=False)}"
        image_models_code = f"image_models = {json.dumps(image_models, ensure_ascii=False)}"
        vision_models_code = f"vision_models = {json.dumps(vision_models, ensure_ascii=False)}"
        
        # Combina tudo
        code = f"""{models_code}

{text_models_code}

{image_models_code}

{vision_models_code}
"""
        return code


def main():
    """Função principal para testar o gerador."""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python models_generator.py <arquivo_json_ou_texto>")
        print("\nExemplo:")
        print("  python models_generator.py dados_lmarena.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = f.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{input_file}' não encontrado.")
        sys.exit(1)
    
    # Extrai os modelos
    models = ModelsGenerator.extract_initial_models(raw_data)
    
    if not models:
        print("Nenhum modelo encontrado nos dados.")
        sys.exit(1)
    
    print(f"Encontrados {len(models)} modelos.")
    print("\n" + "=" * 80 + "\n")
    
    # Gera o código
    code = ModelsGenerator.generate_full_code(models)
    print(code)
    
    # Opcionalmente, salva em arquivo
    output_file = input_file.replace('.json', '_models.py').replace('.txt', '_models.py')
    if output_file != input_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"\nCódigo salvo em: {output_file}")


def example_extract_and_save_json():
    """Exemplo único: Extrair modelos do payload next_f.push e salvar em JSON."""
    print("=" * 80)
    print("Exemplo: Extraindo modelos do payload next_f.push e salvando em JSON")
    print("=" * 80)
    
    # Payload bruto do next_f.push
    raw_data = r"""self.__next_f.push([1,"5:[\"$\",\"$L1e\",null,{\"state\":{\"mutations\":[],\"queries\":[{\"dehydratedAt\":1760641869254,\"state\":{\"data\":{\"pages\":[{\"history\":[],\"pagination\":{\"cursor\":null,\"hasMore\":false,\"limit\":1}}],\"pageParams\":[null]},\"dataUpdateCount\":1,\"dataUpdatedAt\":1760641869048,\"error\":null,\"errorUpdateCount\":0,\"errorUpdatedAt\":0,\"fetchFailureCount\":0,\"fetchFailureReason\":null,\"fetchMeta\":null,\"isInvalidated\":false,\"status\":\"success\",\"fetchStatus\":\"idle\"},\"queryKey\":[\"history\",\"list\"],\"queryHash\":\"[\\\"history\\\",\\\"list\\\"]\"}]},\"data-sentry-element\":\"HydrationBoundary\",\"data-sentry-component\":\"LayoutWithSidebar\",\"data-sentry-source-file\":\"layout.tsx\",\"children\":[\"$\",\"$L1f\",null,{\"initialState\":\"$undefined\",\"data-sentry-element\":\"EvaluationStoreProvider\",\"data-sentry-source-file\":\"layout.tsx\",\"children\":[\"$\",\"$L20\",null,{\"initialModels\":[{\"id\":\"e2d9d353-6dbe-4414-bf87-bd289d523726\",\"publicName\":\"gemini-2.5-pro\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":1},{\"id\":\"51a47cc6-5ef9-4ac7-a59c-4009230d7564\",\"publicName\":\"gemini-2.5-pro-grounding-exp\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"rank\":1},{\"id\":\"f1a2eb6f-fc30-4806-9e00-1efd0d73cbc4\",\"publicName\":\"claude-opus-4-1-20250805-thinking-16k\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":1},{\"id\":\"b0ea1407-2f92-4515-b9cc-b22a6d6c14f2\",\"publicName\":\"claude-sonnet-4-5-20250929-thinking-32k\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":1},{\"id\":\"983bc566-b783-4d28-b24c-3c8b08eb1086\",\"publicName\":\"gpt-5-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":2},{\"id\":\"cb0f1e24-e8e9-4745-aabc-b926ffde7475\",\"publicName\":\"o3-2025-04-16\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":2},{\"id\":\"0199c1d5-3b2b-7b29-be19-58f2a6fc86ba\",\"publicName\":\"claude-sonnet-4-5-20250929\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":2},{\"id\":\"96ae95fd-b70d-49c3-91cc-b58c7da1090b\",\"publicName\":\"claude-opus-4-1-20250805\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":2},{\"id\":\"0199c1e0-3720-742d-91c8-787788b0a19b\",\"publicName\":\"chatgpt-4o-latest-20250326\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"web\":true,\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":2},{\"id\":\"812c93cc-5f88-4cff-b9ca-c11a26599b0e\",\"publicName\":\"qwen3-max-preview\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":3},{\"id\":\"98ad8b8b-12cd-46cd-98de-99edde7e03eb\",\"publicName\":\"qwen3-max-2025-09-23\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":8},{\"id\":\"4b11c78c-08c8-461c-938e-5fc97d56a40d\",\"publicName\":\"gpt-5-chat\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":9},{\"id\":\"d4cdb846-a711-4b2b-9de1-63a852c2c99c\",\"publicName\":\"deepseek-v3.2-exp-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"deepseek\",\"provider\":\"deepseek\",\"rank\":9},{\"id\":\"71023e9b-7361-498a-b6db-f2d2a83883fd\",\"publicName\":\"grok-4-fast\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xai\",\"provider\":\"xaiResearch\",\"rank\":9},{\"id\":\"f595e6f1-6175-4880-a9eb-377e390819e4\",\"publicName\":\"glm-4.6\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"zai\",\"provider\":\"zai\",\"rank\":9},{\"id\":\"3b5e9593-3dc0-4492-a3da-19784c4bde75\",\"publicName\":\"claude-opus-4-20250514-thinking-16k\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":11},{\"id\":\"ee7cb86e-8601-4585-b1d0-7c7380f8f6f4\",\"publicName\":\"qwen3-235b-a22b-instruct-2507\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":11},{\"id\":\"84efc8b9-a441-4614-a4ff-6398f8bd34eb\",\"publicName\":\"deepseek-v3.2-exp\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"deepseek\",\"provider\":\"deepseek\",\"rank\":11},{\"id\":\"716aa8ca-d729-427f-93ab-9579e4a13e98\",\"publicName\":\"qwen3-vl-235b-a22b-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":11},{\"id\":\"b9edb8e9-4e98-49e7-8aaf-ae67e9797a11\",\"publicName\":\"grok-4-0709\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xai\",\"provider\":\"openrouter\",\"rank\":12},{\"id\":\"ee116d12-64d6-48a8-88e5-b2d06325cdd2\",\"publicName\":\"claude-opus-4-20250514\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":13},{\"id\":\"14e9311c-94d2-40c2-8c54-273947e208b0\",\"publicName\":\"gpt-4.1-2025-04-14\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":13},{\"id\":\"fc700d46-c4c1-4fec-88b5-f086876ae0bb\",\"publicName\":\"gemini-2.5-flash-preview-09-2025\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":14},{\"id\":\"ce2092c1-28d4-4d42-a1e0-6b061dfe0b20\",\"publicName\":\"gemini-2.5-flash\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":15},{\"id\":\"27035fb8-a25b-4ec9-8410-34be18328afd\",\"publicName\":\"mistral-medium-2508\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"mistral\",\"provider\":\"mistral\",\"rank\":15},{\"id\":\"d079ef40-3b20-4c58-ab5e-243738dbada5\",\"publicName\":\"glm-4.5\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"zai\",\"provider\":\"zai\",\"rank\":16},{\"id\":\"351fe482-eb6c-4536-857b-909e16c0bf52\",\"publicName\":\"qwen3-next-80b-a3b-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":22},{\"id\":\"6fcbe051-f521-4dc7-8986-c429eb6191bf\",\"publicName\":\"longcat-flash-chat\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"meituan\",\"provider\":\"meituan\",\"rank\":26},{\"id\":\"4653dded-a46b-442a-a8fe-9bb9730e2453\",\"publicName\":\"claude-sonnet-4-20250514-thinking-32k\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":32},{\"id\":\"1a400d9a-f61c-4bc2-89b4-a9b7e77dff12\",\"publicName\":\"qwen3-235b-a22b-no-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":33},{\"id\":\"5fd3caa8-fe4c-41a5-a22c-0025b58f4b42\",\"publicName\":\"gpt-5-mini-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":34},{\"id\":\"f1102bbf-34ca-468f-a9fc-14bcf63f315b\",\"publicName\":\"o4-mini-2025-04-16\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":36},{\"id\":\"2f5253e4-75be-473c-bcfc-baeb3df0f8ad\",\"publicName\":\"deepseek-v3-0324\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"deepseek\",\"provider\":\"fireworks\",\"rank\":36},{\"id\":\"23848331-9f93-404f-85f0-3c3b4ece177e\",\"publicName\":\"mai-1-preview\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"microsoft-ai\",\"provider\":\"microsoftAi\",\"rank\":36},{\"id\":\"03c511f5-0d35-4751-aae6-24f918b0d49e\",\"publicName\":\"qwen3-vl-235b-a22b-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":36},{\"id\":\"ac44dd10-0666-451c-b824-386ccfea7bcc\",\"publicName\":\"claude-sonnet-4-20250514\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":39},{\"id\":\"a8d1d310-e485-4c50-8f27-4bff18292a99\",\"publicName\":\"qwen3-30b-a3b-instruct-2507\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":40},{\"id\":\"be98fcfd-345c-4ae1-9a82-a19123ebf1d2\",\"publicName\":\"claude-3-7-sonnet-20250219-thinking-32k\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":41},{\"id\":\"af033cbd-ec6c-42cc-9afa-e227fc12efe8\",\"publicName\":\"qwen3-coder-480b-a35b-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"Alibaba\",\"provider\":\"alibaba\",\"rank\":42},{\"id\":\"27b9f8c6-3ee1-464a-9479-a8b3c2a48fd4\",\"publicName\":\"mistral-medium-2505\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"mistral\",\"provider\":\"mistral\",\"rank\":45},{\"id\":\"6a5437a7-c786-467b-b701-17b0bc8c8231\",\"publicName\":\"gpt-4.1-mini-2025-04-14\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":46},{\"id\":\"2595a594-fa54-4299-97cd-2d7380d21c80\",\"publicName\":\"qwen3-235b-a22b\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":52},{\"id\":\"73cf8705-98c8-4b75-8d04-e3746e1c1565\",\"publicName\":\"qwen3-next-80b-a3b-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":54},{\"id\":\"7bfb254a-5d32-4ce2-b6dc-2c7faf1d5fe8\",\"publicName\":\"glm-4.5-air\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"zai\",\"provider\":\"zai\",\"rank\":55},{\"id\":\"c5a11495-081a-4dc6-8d9a-64a4fd6f7bbc\",\"publicName\":\"claude-3-7-sonnet-20250219\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"web\":true,\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":55},{\"id\":\"87e8d160-049e-4b4e-adc4-7f2511348539\",\"publicName\":\"minimax-m1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"minimax\",\"provider\":\"minimax\",\"rank\":56},{\"id\":\"f44e280a-7914-43ca-a25d-ecfcc5d48d09\",\"publicName\":\"claude-3-5-sonnet-20241022\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"web\":true,\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":56},{\"id\":\"149619f1-f1d5-45fd-a53e-7d790f156f20\",\"publicName\":\"grok-3-mini-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xai\",\"provider\":\"xaiPublic\",\"rank\":56},{\"id\":\"789e245f-eafe-4c72-b563-d135e93988fc\",\"publicName\":\"gemma-3-27b-it\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":60},{\"id\":\"7a55108b-b997-4cff-a72f-5aa83beee918\",\"publicName\":\"gemini-2.0-flash-001\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":60},{\"id\":\"7699c8d4-0742-42f9-a117-d10e84688dab\",\"publicName\":\"grok-3-mini-beta\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xai\",\"provider\":\"xaiPublic\",\"rank\":63},{\"id\":\"9dab0475-a0cc-4524-84a2-3fd25aa8c768\",\"publicName\":\"glm-4.5v\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"zai\",\"provider\":\"zai\",\"rank\":63},{\"id\":\"71f96ca9-4cf8-4be7-bac2-2231613930a6\",\"publicName\":\"ling-flash-2.0\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"ant-group\",\"provider\":\"antgroup\",\"rank\":63},{\"id\":\"bbad1d17-6aa5-4321-949c-d11fb6289241\",\"publicName\":\"mistral-small-2506\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"mistral\",\"provider\":\"mistral\",\"rank\":65},{\"id\":\"0f785ba1-efcb-472d-961e-69f7b251c7e3\",\"publicName\":\"command-a-03-2025\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"cohere\",\"provider\":\"cohere\",\"rank\":67},{\"id\":\"6ee9f901-17b5-4fbe-9cc2-13c16497c23b\",\"publicName\":\"gpt-oss-120b\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"fireworks\",\"rank\":67},{\"id\":\"c680645e-efac-4a81-b0af-da16902b2541\",\"publicName\":\"o3-mini\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":69},{\"id\":\"1ea13a81-93a7-4804-bcdd-693cd72e302d\",\"publicName\":\"step-3\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"stepfun\",\"provider\":\"stepfun\",\"rank\":69},{\"id\":\"2dc249b3-98da-44b4-8d1e-6666346a8012\",\"publicName\":\"gpt-5-nano-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":72},{\"id\":\"885976d3-d178-48f5-a3f4-6e13e0718872\",\"publicName\":\"qwq-32b\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":79},{\"id\":\"b5ad3ab7-fc56-4ecd-8921-bd56b55c1159\",\"publicName\":\"llama-4-maverick-17b-128e-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"meta\",\"provider\":\"fireworks\",\"rank\":86},{\"id\":\"9a066f6a-7205-4325-8d0b-d81cc4b049c0\",\"publicName\":\"qwen3-30b-a3b\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":89},{\"id\":\"11ad4114-c868-4fed-b6e7-d535dc9c62f8\",\"publicName\":\"ring-flash-2.0\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"ant-group\",\"provider\":\"antgroup\",\"rank\":95},{\"id\":\"f6fbf06c-532c-4c8a-89c7-f3ddcfb34bd1\",\"publicName\":\"claude-3-5-haiku-20241022\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"googleVertexAnthropic\",\"rank\":96},{\"id\":\"c28823c1-40fd-4eaf-9825-e28f11d1f8b2\",\"publicName\":\"llama-4-scout-17b-16e-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"meta\",\"provider\":\"fireworks\",\"rank\":96},{\"id\":\"ec3beb4b-7229-4232-bab9-670ee52dd711\",\"publicName\":\"gpt-oss-20b\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"fireworks\",\"rank\":96},{\"id\":\"dcbd7897-5a37-4a34-93f1-76a24c7bb028\",\"publicName\":\"llama-3.3-70b-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"meta\",\"provider\":\"fireworks\",\"rank\":99},{\"id\":\"6337f479-2fc8-4311-a76b-8c957765cd68\",\"publicName\":\"magistral-medium-2506\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"mistral\",\"provider\":\"mistral\",\"rank\":116},{\"id\":\"69f5d38a-45f5-4d3a-9320-b866a4035ed9\",\"publicName\":\"mistral-small-3.1-24b-instruct-2503\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"mistral\",\"provider\":\"mistral\",\"rank\":123},{\"id\":\"0199de70-e6ad-7276-9020-a7502bed99ad\",\"publicName\":\"flying-octopus\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"4ddb69f5-391a-4f78-af92-7d7328c18ab1\",\"publicName\":\"ibm-granite-h-small\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"ibm\",\"provider\":\"ibm\"},{\"id\":\"42015285-534d-4e6b-9a9a-9061c2f73e1c\",\"publicName\":\"x1-1-preview-0915\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"6a3a1e04-050e-4cb4-9052-b9ac4bec0c38\",\"publicName\":\"hunyuan-vision-1.5-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"tencent\",\"provider\":\"tencent\"},{\"id\":\"04ec9a17-c597-49df-acf0-963da275c246\",\"publicName\":\"gemini-2.5-flash-lite-preview-06-17-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\"},{\"id\":\"0199e3d1-a308-77b9-a650-41453e8ef2fb\",\"publicName\":\"qwen3-vl-8b-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"0199e3d1-a713-7de2-a5dd-a1583cad9532\",\"publicName\":\"qwen3-vl-8b-instruct\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"b4a681ed-df4e-476f-89c6-a992a5783e60\",\"publicName\":\"EB45-turbo-vl-0906\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"39b185cb-aba9-4232-99ea-074883a5ccd4\",\"publicName\":\"stephen-v2\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e459-d40d-70dd-9318-a397759e271b\",\"publicName\":\"phantom-0919-3\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"8d1f38a1-51a6-4030-ae4b-e19fb503e4fa\",\"publicName\":\"x1-turbo-0906\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199c1d5-51b8-7ead-a0a8-3f59234682fa\",\"publicName\":\"gpt-5-high-no-system-prompt\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"web\":false,\"code\":false,\"text\":true,\"image\":false,\"video\":false,\"search\":false}}},{\"id\":\"0199e53f-f5ab-7755-ba39-7983e09a2eb3\",\"publicName\":\"phantom-0925-1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"49bd7403-c7fd-4d91-9829-90a91906ad6c\",\"publicName\":\"llama-4-maverick-03-26-experimental\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"meta\",\"provider\":\"meta\"},{\"id\":\"5f2ced37-e2f0-4ddd-9e5a-7ddd13c32564\",\"publicName\":\"anonymous-922\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"48fe3167-5680-4903-9ab5-2f0b9dc05815\",\"publicName\":\"nightride-on\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"638fb8b8-1037-4ee5-bfba-333392575a5d\",\"publicName\":\"EB45-vision\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"c822ec98-38e9-4e43-a434-982eb534824f\",\"publicName\":\"nightride-on-v2\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"c15b93ed-e87b-467f-8f9f-d830fd7aa54d\",\"publicName\":\"lmarena-internal-test-only\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"f1a5a6ab-e1b1-4247-88ac-49395291c1e3\",\"publicName\":\"not-a-new-model\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"e9dd5a96-c066-48b0-869f-eb762030b5ed\",\"publicName\":\"EB45-turbo\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"24d647d0-7945-442d-b323-08ca04e9e288\",\"publicName\":\"sorting-hat\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e649-cdfb-75ee-848d-af9794d91c27\",\"publicName\":\"shasta\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"9af435c8-1f53-4b78-a400-c1f5e9fe09b0\",\"publicName\":\"leepwal\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e649-e3ac-7057-a099-95a3a852048f\",\"publicName\":\"acadia\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e649-eef5-78b8-abe1-efea19dd3e32\",\"publicName\":\"sierra\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"ac31e980-8bf1-4637-adba-cf9ffa8b6343\",\"publicName\":\"qwen3-max-2025-09-26\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"f23d6df4-4395-4404-897f-bdedc909e783\",\"publicName\":\"raptor\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"19b3730a-0369-49ba-ad9c-09e7337937f0\",\"publicName\":\"grok-4-fast-reasoning\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xai\",\"provider\":\"xaiPublic\"},{\"id\":\"1c0259b5-dff7-48ce-bca1-b6957675463b\",\"publicName\":\"MiMo-VL-7B-RL-2508\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xiaomi\",\"provider\":\"xiaomiVision\"},{\"id\":\"75555628-8c14-402a-8d6e-43c19cb40116\",\"publicName\":\"gemini-2.5-flash-lite-preview-09-2025-no-thinking\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"google\",\"provider\":\"google\"},{\"id\":\"d923ef23-fe78-47c0-94cf-360316a9d96e\",\"publicName\":\"x1-1-peach\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"d5a306db-1bca-41c8-9d62-681b0fc53f23\",\"publicName\":\"x1-1-kiwifruit\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"d7c41f1d-6723-45da-af2a-ec4a405732e5\",\"publicName\":\"polaris\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"5c29b9af-1dfe-4460-9ca0-e12c80d5f83b\",\"publicName\":\"raptor-0929\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"e3c9ea42-5f42-496b-bc80-c7e8ee5653cc\",\"publicName\":\"stephen-vision-csfix\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"19ad5f04-38c6-48ae-b826-f7d5bbfd79f7\",\"publicName\":\"gpt-5-high-new-system-prompt\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"openai\",\"provider\":\"openai\"},{\"id\":\"0199c9dc-e157-7458-bd49-5942363be215\",\"publicName\":\"qwen3-omni-flash\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"ee3588cd-1fe1-484a-bcc9-f92065b8380c\",\"publicName\":\"MiMo-7B\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"xiaomi\",\"provider\":\"xiaomi\"},{\"id\":\"0199e649-f35d-7c28-84c0-286dae3421b6\",\"publicName\":\"miramar\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0304b4de-e544-48d4-8490-ad9123bc26e3\",\"publicName\":\"monster\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e649-f874-714d-9a83-1be237cc41e6\",\"publicName\":\"aspen\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199e649-fc24-7e2b-80f5-149af6456ee9\",\"publicName\":\"solitude\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199eb4b-6eb2-7b47-a380-830eabe502f9\",\"publicName\":\"zion\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199eb4b-73a6-71ae-b289-abe0c945e0c2\",\"publicName\":\"vail\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"6fe1ec40-3219-4c33-b3e7-0e65658b4194\",\"publicName\":\"qwen-vl-max-2025-08-13\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"0199e8e9-01ed-73e0-96ba-cf43b286bf10\",\"publicName\":\"claude-haiku-4-5-20251001\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}},\"organization\":\"anthropic\",\"provider\":\"anthropic\"},{\"id\":\"0199e973-1217-7576-a2a2-eafa353704b8\",\"publicName\":\"ernie-exp-251015\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199eb70-d0d9-7a6c-b6f8-1c5bd0b0dec3\",\"publicName\":\"ernie-exp-251016\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199eb70-db25-73ea-b944-f18fe0c3c0cd\",\"publicName\":\"ernie-exp-vl-251016\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0b44df22-b61c-4999-b3b7-d6dca4f3b31d\",\"publicName\":\"ernie-exp-vl-250930\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199c2e4-f2cd-73d9-aa7a-952437fcaf1d\",\"publicName\":\"phantom-0930-1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199c2e4-ff43-7524-8afe-154bd5fdc925\",\"publicName\":\"phantom-0930-2\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"0199edd2-88be-76b8-9aaa-5fc6b9c53503\",\"publicName\":\"ling-1t\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"text\":true}}},{\"id\":\"e884e85b-c998-44d8-b38d-db42a300a318\",\"publicName\":\"gemini-2.5-flash-image-preview (nano-banana)\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"google-genai\",\"rank\":1},{\"id\":\"101ad96b-bf08-47dc-9985-da21fca4c720\",\"publicName\":\"hpb\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"rank\":1},{\"id\":\"7766a45c-1b6b-4fb8-9823-2557291e1ddd\",\"publicName\":\"hunyuan-image-3.0\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"tencent\",\"provider\":\"tencent\",\"rank\":1},{\"id\":\"f8aec69d-e077-4ed1-99be-d34f48559bbf\",\"publicName\":\"imagen-4.0-ultra-generate-preview-06-06\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"googleVertex\",\"rank\":3},{\"id\":\"32974d8d-333c-4d2e-abf3-f258c0ac1310\",\"publicName\":\"seedream-4-high-res-fal\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"bytedance\",\"provider\":\"fal\",\"rank\":4},{\"id\":\"2ec9f1a6-126f-4c65-a102-15ac401dcea4\",\"publicName\":\"imagen-4.0-generate-preview-06-06\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"googleVertex\",\"rank\":6},{\"id\":\"69f90b32-01dc-43e1-8c48-bf494f8f4f38\",\"publicName\":\"gpt-image-1-high-fidelity\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"rank\":8},{\"id\":\"6e855f13-55d7-4127-8656-9168a9f4dcc0\",\"publicName\":\"gpt-image-1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"openai\",\"provider\":\"customOpenai\",\"rank\":8},{\"id\":\"0199c238-f8ee-7f7d-afc1-7e28fcfd21cf\",\"publicName\":\"gpt-image-1-mini\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"openai\",\"provider\":\"customOpenai\",\"rank\":9},{\"id\":\"1b407d5c-1806-477c-90a5-e5c5a114f3bc\",\"publicName\":\"mai-image-1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"microsoft-ai\",\"provider\":\"maiImage\",\"rank\":11},{\"id\":\"d8771262-8248-4372-90d5-eb41910db034\",\"publicName\":\"seedream-3\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"bytedance\",\"provider\":\"fal\",\"rank\":15},{\"id\":\"0633b1ef-289f-49d4-a834-3d475a25e46b\",\"publicName\":\"flux-1-kontext-max\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"rank\":16},{\"id\":\"0199e980-d247-7dd3-9ca1-77092f126f05\",\"publicName\":\"hunyuan-image-3.0-fal\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"rank\":16},{\"id\":\"9fe82ee1-c84f-417f-b0e7-cab4ae4cf3f3\",\"publicName\":\"qwen-image-prompt-extend\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"alibaba\",\"provider\":\"alibaba\",\"rank\":19},{\"id\":\"51ad1d79-61e2-414c-99e3-faeb64bb6b1b\",\"publicName\":\"imagen-3.0-generate-002\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"googleVertex\",\"rank\":21},{\"id\":\"28a8f330-3554-448c-9f32-2c0a08ec6477\",\"publicName\":\"flux-1-kontext-pro\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"bfl\",\"provider\":\"bfl\",\"rank\":21},{\"id\":\"73378be5-cdba-49e7-b3d0-027949871aa6\",\"publicName\":\"ideogram-v3-quality\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"Ideogram\",\"provider\":\"fal\",\"rank\":26},{\"id\":\"f44fd4f8-af30-480f-8ce2-80b2bdfea55e\",\"publicName\":\"imagen-4.0-fast-generate-001\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"googleVertex\",\"rank\":27},{\"id\":\"5a3b3520-c87d-481f-953c-1364687b6e8f\",\"publicName\":\"lucid-origin\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"leonardo-ai\",\"provider\":\"leonardo-ai\",\"rank\":29},{\"id\":\"e7c9fa2d-6f5d-40eb-8305-0980b11c7cab\",\"publicName\":\"photon\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"luma-ai\",\"provider\":\"fal\",\"rank\":30},{\"id\":\"b88d5814-1d20-49cc-9eb6-e362f5851661\",\"publicName\":\"recraft-v3\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"Recraft\",\"provider\":\"fal\",\"rank\":33},{\"id\":\"69bbf7d4-9f44-447e-a868-abc4f7a31810\",\"publicName\":\"gemini-2.0-flash-preview-image-generation\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"google\",\"provider\":\"google\",\"rank\":41},{\"id\":\"bb97bc68-131c-4ea4-a59e-03a6252de0d2\",\"publicName\":\"dall-e-3\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"openai\",\"provider\":\"openai\",\"rank\":42},{\"id\":\"eb90ae46-a73a-4f27-be8b-40f090592c9a\",\"publicName\":\"flux-1-kontext-dev\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"bfl\",\"provider\":\"bfl\",\"rank\":43},{\"id\":\"a9a26426-5377-4efa-bef9-de71e29ad943\",\"publicName\":\"hunyuan-image-2.1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"tencent\",\"provider\":\"fal\",\"rank\":45},{\"id\":\"32bff2df-00e6-409b-ad3f-bfbad87cc49f\",\"publicName\":\"hidream-e1.1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false,\"requiresUpload\":true}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}}},{\"id\":\"995cf221-af30-466d-a809-8e0985f83649\",\"publicName\":\"qwen-image-edit\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false,\"requiresUpload\":true}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"alibaba\",\"provider\":\"alibaba\"},{\"id\":\"e2969ebb-6450-4bc4-87c9-bbdcf95840da\",\"publicName\":\"seededit-3.0\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":false,\"requiresUpload\":true}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}}},{\"id\":\"0199e980-ba42-737b-9436-927b6e7ca73e\",\"publicName\":\"reve-v1\",\"capabilities\":{\"inputCapabilities\":{\"text\":true,\"image\":{\"multipleImages\":true,\"requiresUpload\":true}},\"outputCapabilities\":{\"image\":{\"aspectRatios\":[\"1:1\"]}}},\"organization\":\"reve\",\"provider\":\"reve\"},{\"id\":\"9217ac2d-91bc-4391-aa07-b8f9e2cf11f2\",\"publicName\":\"grok-4-fast-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"xai\",\"provider\":\"xaiResearchSearch\",\"rank\":1},{\"id\":\"b222be23-bd55-4b20-930b-a30cc84d3afd\",\"publicName\":\"gemini-2.5-pro-grounding\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"google\",\"provider\":\"googleVertex\",\"rank\":2},{\"id\":\"c8711485-d061-4a00-94d2-26c31b840a3d\",\"publicName\":\"ppl-sonar-pro-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"perplexity\",\"provider\":\"perplexity\",\"rank\":2},{\"id\":\"fbe08e9a-3805-4f9f-a085-7bc38e4b51d1\",\"publicName\":\"o3-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"openai\",\"provider\":\"openaiResponses\",\"rank\":2},{\"id\":\"86d767b0-2574-4e47-a256-a22bcace9f56\",\"publicName\":\"grok-4-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"xai\",\"provider\":\"xaiSearch\",\"rank\":2},{\"id\":\"d14d9b23-1e46-4659-b157-a3804ba7e2ef\",\"publicName\":\"gpt-5-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"openai\",\"provider\":\"openaiResponses\",\"rank\":2},{\"id\":\"25bcb878-749e-49f4-ac05-de84d964bcee\",\"publicName\":\"claude-opus-4-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"anthropic\",\"provider\":\"anthropicSearch\",\"rank\":6},{\"id\":\"d942b564-191c-41c5-ae22-400a930a2cfe\",\"publicName\":\"claude-opus-4-1-search\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"anthropic\",\"provider\":\"anthropicSearch\",\"rank\":6},{\"id\":\"24145149-86c9-4690-b7c9-79c7db216e5c\",\"publicName\":\"ppl-sonar-reasoning-pro-high\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"perplexity\",\"provider\":\"perplexity\",\"rank\":9},{\"id\":\"0862885e-ef53-4d0d-b9c4-4c8f68f453ce\",\"publicName\":\"diffbot-small-xl\",\"capabilities\":{\"inputCapabilities\":{\"text\":true},\"outputCapabilities\":{\"search\":true}},\"organization\":\"diffbot\",\"provider\":\"diffbot\",\"rank\":10}],\"initialModelAId\":null,\"initialModelBId\":null,\"data-sentry-element\":\"ModelStoreProvider\",\"data-sentry-source-file\":\"layout.tsx\",\"children\":\"$L21\"}]}]}]\n"])"""
    
    # Extrai os modelos
    models = ModelsGenerator.extract_initial_models(raw_data)
    print(f"\n✓ Extraídos {len(models)} modelos")
    
    # Extrai categorias
    text_models = ModelsGenerator.extract_text_models(models)
    image_models = ModelsGenerator.extract_image_models(models)
    vision_models = ModelsGenerator.extract_vision_models(models)
    
    print(f"✓ Modelos de texto: {len(text_models)}")
    print(f"✓ Modelos de imagem: {len(image_models)}")
    print(f"✓ Modelos com visão: {len(vision_models)}")
    
    # Prepara dados para salvar
    output_data = {
        "models": models,
        "text_models": text_models,
        "image_models": image_models,
        "vision_models": vision_models,
        "summary": {
            "total_models": len(models),
            "text_models_count": len(text_models),
            "image_models_count": len(image_models),
            "vision_models_count": len(vision_models)
        }
    }
    
    # Salva em JSON
    output_file = "extracted_models.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Dados salvos em: {output_file}")







if __name__ == "__main__":
    import sys
    
    # Se executado sem argumentos, roda o exemplo
    if len(sys.argv) < 2:
        example_extract_and_save_json()
    else:
        main()
