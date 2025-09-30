# WSL Docker Cleaner - Guia de Uso

## 📋 Descrição
Scripts Python para reduzir significativamente o tamanho dos arquivos WSL Docker no Windows 11, 
baseado nas melhores práticas atuais de 2025.

## 🚀 Scripts Incluídos

### 1. wsl_docker_cleaner.py (Completo)
- Limpeza abrangente do Docker (containers, imagens, volumes, redes)
- Configuração automática do modo sparse no WSL2
- Compactação otimizada dos arquivos VHDX
- Relatórios detalhados e logs completos
- Limpeza de arquivos temporários

### 2. quick_wsl_cleanup.py (Rápido)
- Versão simplificada para uso rápido
- Foca nas operações mais importantes
- Ideal para limpeza regular

## ⚡ Como Usar

### Preparação:
```bash
# Instalar dependência (se necessário)
pip install psutil

# Dar permissões de administrador (recomendado)
# Executar como administrador para compactação VHDX
```

### Execução:
```bash
# Script completo
python wsl_docker_cleaner.py

# Script rápido
python quick_wsl_cleanup.py
```

## 🛠️ O que o Script Faz

### 1. Limpeza do Docker:
- `docker stop $(docker ps -aq)` - Para todos containers
- `docker container prune -f` - Remove containers parados
- `docker image prune -af` - Remove imagens não utilizadas
- `docker volume prune -f` - Remove volumes órfãos
- `docker network prune -f` - Remove redes não utilizadas
- `docker system prune -af --volumes` - Limpeza completa
- `docker builder prune -af` - Limpa cache de build

### 2. Configuração WSL:
- Ativa modo `sparseVhd=true` no .wslconfig
- Configura sparse para distribuições Docker
- Otimiza configurações de memória

### 3. Compactação VHDX:
- Usa `Optimize-VHD -Mode Full` do PowerShell
- Compacta arquivos em `%LOCALAPPDATA%\Docker\wsl\`
- Recupera espaço significativo do disco

### 4. Limpeza Adicional:
- Remove logs temporários do Docker
- Limpa cache do sistema
- Remove arquivos desnecessários

## 📊 Resultados Esperados

### Economia Típica:
- **Docker pequeno**: 2-5 GB recuperados
- **Docker médio**: 10-20 GB recuperados  
- **Docker pesado**: 30+ GB recuperados

### Localizações dos VHDX:
```
%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx
%LOCALAPPDATA%\Docker\wsl\distro\ext4.vhdx
```

## 🔧 Configurações Recomendadas

### Arquivo .wslconfig (criado automaticamente):
```ini
[wsl2]
sparseVhd=true
memory=4GB
processors=4
swap=2GB
swapFile=%TEMP%\wsl-swap.vhdx
```

### Limpeza Automática Docker:
```bash
# Configurar limpeza automática (executar no Docker)
docker system events --filter event=delete
```

## 📝 Manutenção Regular

### Frequência Recomendada:
- **Uso intenso**: Semanal
- **Uso normal**: Mensal
- **Uso leve**: Trimestral

### Comandos Manuais Úteis:
```bash
# Verificar espaço usado pelo Docker
docker system df

# Ver tamanho das imagens
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Monitorar distribuições WSL
wsl -l -v

# Verificar status do Docker
docker info
```

## ⚠️ Avisos Importantes

### Requisitos:
- Windows 11 com WSL2
- Docker Desktop instalado
- Python 3.7+ com pip
- Permissões de administrador (recomendado)

### Precauções:
- ⚠️ **Backup**: Faça backup de containers importantes antes da limpeza
- ⚠️ **Containers ativos**: Script para containers em execução
- ⚠️ **Dados**: Volumes importantes podem ser removidos na limpeza completa
- ⚠️ **Tempo**: Processo pode demorar 10-30 minutos dependendo do tamanho

### Verificações Pré-Limpeza:
```bash
# Ver containers importantes
docker ps -a

# Ver imagens importantes  
docker images

# Ver volumes importantes
docker volume ls

# Fazer backup se necessário
docker save -o backup.tar image_name:tag
```

## 🐛 Solução de Problemas

### Erros Comuns:

1. **"Docker não encontrado"**
   - Verificar se Docker Desktop está instalado
   - Adicionar Docker ao PATH do sistema

2. **"Acesso negado no VHDX"**
   - Executar como administrador
   - Fechar Docker Desktop completamente
   - Executar `wsl --shutdown`

3. **"Optimize-VHD não encontrado"**
   - Habilitar Hyper-V no Windows
   - Executar em PowerShell como admin

4. **"Timeout nos comandos"**
   - Docker com muitos dados pode demorar
   - Executar limpeza manual primeiro

### Log e Debug:
- Logs salvos em: `wsl_docker_cleanup.log`
- Verificar saída detalhada dos comandos
- Executar comandos individuais se necessário

## 🔍 Monitoramento Contínuo

### Scripts Complementares:
```python
# Verificar tamanho dos VHDX
import os
vhdx = r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx"
if os.path.exists(os.path.expandvars(vhdx)):
    size = os.path.getsize(os.path.expandvars(vhdx)) / (1024**3)
    print(f"VHDX Docker: {size:.2f} GB")
```

### Alertas de Tamanho:
- Configurar alerta quando VHDX > 20 GB
- Monitorar crescimento semanal
- Automatizar limpeza quando necessário

## 📚 Referências Técnicas
- [Microsoft WSL Disk Space](web:16)
- [Docker System Prune](web:7) 
- [WSL2 Performance](web:3)
- [VHDX Optimization](web:10)

---
**Versão**: 1.0  
**Data**: Setembro 2025  
**Compatibilidade**: Windows 11 + Docker Desktop + WSL2
