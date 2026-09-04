## Deploy rápido para VPS (IP público:80)

Adicionei um docker-compose.yml e um script deploy.sh para facilitar deploy numa VPS com IP público.

Passos mínimos no teu VPS (resumo):
1) Criar VPS Ubuntu e abrir porta 80 no firewall do provedor
2) Copiar a tua chave SSH para o painel ou usar login por password
3) Localmente executar:
   chmod +x deploy.sh
   ./deploy.sh ubuntu@SEU_IP [/caminho/da/chave]

O script fará:
- instalar docker e docker-compose
- clonar o repositório em /tmp e mover para /opt/android-rat
- buildar a imagem e subir com docker-compose (mapear 80:80)

Variáveis de ambiente importantes (definir no servidor antes do docker-compose up):
- JWT_SECRET (muda isto!)
- FLASK_SECRET (muda isto!)
- ADMIN_USER (opcional)
- ADMIN_PASS (muda isto!)

Exemplo de comando (no servidor, antes de subir):

export JWT_SECRET='troca_isto'
export FLASK_SECRET='troca_isto'
export ADMIN_USER='admin'
export ADMIN_PASS='admin123'

# depois: docker-compose up -d

Notas:
- O script é uma conveniência; ajusta-o ao teu ambiente (paths, user, segurança).
- Recomendo trocar a senha admin e gerir secrets com método seguro (env vars, Vault).
- Este deploy expõe HTTP em :80. Se precisares de TLS por IP, será necessário um domínio e proxy com TLS.
