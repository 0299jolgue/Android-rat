# Android-rat — Painel de Gestão (legítimo)

Este repositório contém um esqueleto de painel web para gestão remota
consentida de dispositivos Android (MDM / suporte remoto). É responsabilidade do
proprietário usar apenas com consentimento explícito dos dispositivos alvo.

Arquivos adicionados:
- starter.py          -> aplicação Flask + Flask-SocketIO (porta 80)
- requirements.txt    -> dependências Python
- templates/          -> arquivos HTML do dashboard
- static/             -> CSS e JS mínimos
- Dockerfile          -> container básico para servir na porta 80

Como rodar localmente:
1. export JWT_SECRET='muda_isso'
2. pip install -r requirements.txt
3. sudo python starter.py    # porta 80 precisa de permissão

Ou usando Docker:
  docker build -t android-rat-dashboard .
  docker run -p 80:80 android-rat-dashboard
