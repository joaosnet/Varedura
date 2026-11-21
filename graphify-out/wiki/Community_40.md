# Community 40

> 25 nodes · cohesion 0.10

## Key Concepts

- **SpeedTestProvider** (13 connections) — `monitor/speed_providers.py`
- **MultiProviderSpeedTester** (8 connections) — `monitor/speed_providers.py`
- **SpeedTestResult** (8 connections) — `monitor/speed_providers.py`
- **.__init__()** (6 connections) — `monitor/speed_providers.py`
- **.get_available_providers()** (5 connections) — `monitor/speed_providers.py`
- **.get_next_provider()** (5 connections) — `monitor/speed_providers.py`
- **.run_test_with_fallback()** (5 connections) — `monitor/speed_providers.py`
- **get_multi_provider()** (3 connections) — `monitor/speed_providers.py`
- **.run_test()** (3 connections) — `monitor/speed_providers.py`
- **ABC** (2 connections)
- **.cleanup_active()** (2 connections) — `monitor/speed_providers.py`
- **.cleanup()** (2 connections) — `monitor/speed_providers.py`
- **.is_available()** (2 connections) — `monitor/speed_providers.py`
- **Resultado de um teste de velocidade.** (1 connections) — `monitor/speed_providers.py`
- **Gerenciador de múltiplos provedores de teste de velocidade.** (1 connections) — `monitor/speed_providers.py`
- **Retorna lista de provedores disponíveis.** (1 connections) — `monitor/speed_providers.py`
- **Fecha qualquer driver Selenium em aberto (parada/encerramento). Seguro chamar…** (1 connections) — `monitor/speed_providers.py`
- **Classe base abstrata para provedores de teste de velocidade.** (1 connections) — `monitor/speed_providers.py`
- **Retorna o próximo provedor disponível (rotação round-robin).** (1 connections) — `monitor/speed_providers.py`
- **Executa teste com o próximo provedor na rotação. Cada chamada testa apenas UM…** (1 connections) — `monitor/speed_providers.py`
- **Retorna a instância global do gerenciador de provedores.** (1 connections) — `monitor/speed_providers.py`
- **Verifica se o provedor está disponível (dependências instaladas).** (1 connections) — `monitor/speed_providers.py`
- **Executa o teste de velocidade. Retorna None em caso de erro.** (1 connections) — `monitor/speed_providers.py`
- **Libera recursos do provedor (ex.: fechar driver Selenium). No-op por padrão;…** (1 connections) — `monitor/speed_providers.py`
- **.name()** (1 connections) — `monitor/speed_providers.py`

## Relationships

- [Community 15](Community_15.md) (5 shared connections)
- [Community 71](Community_71.md) (4 shared connections)
- [Community 84](Community_84.md) (3 shared connections)
- [Community 68](Community_68.md) (3 shared connections)
- [Community 48](Community_48.md) (3 shared connections)

## Source Files

- `monitor/speed_providers.py`

## Audit Trail

- EXTRACTED: 47 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*