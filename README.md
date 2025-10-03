````markdown
# Guia de Deploy para Produção

Este documento descreve, passo-a-passo, os comandos e ações necessárias para subir a aplicação em um servidor de produção usando Docker + Nginx + Redis (conforme artefatos adicionados ao repositório).

Observações iniciais
- O guia assume que você fará deploy em um servidor Linux (Ubuntu/Debian/CentOS). Alguns comandos são específicos de shell (bash). Se você operar a partir do PowerShell local, copie os comandos para o shell do servidor.
- Verifique se `docker` e `docker compose` (v2) estão instalados no servidor.
- As instruções usam os arquivos já presentes no repositório: `docker-compose.prod.yml`, `nginx/nginx.conf`, `.env.example`. Ajuste conforme necessário.
- Em produção recomenda-se usar Postgres em vez de SQLite (há notas de como alterar isso abaixo).

1) Preparar o servidor (instalar Docker e Docker Compose)

Em Ubuntu/Debian (execute como root ou com sudo):

```bash
# Guia de Deploy para Produção

Um guia completo para subir a aplicação em produção (Docker + Nginx + Redis).

Sumário
- [Preparar o servidor](#preparar-o-servidor)
- [Clonar o repositório e preparar arquivos](#clonar-o-repositório-e-preparar-arquivos)
- [Certificados TLS](#certificados-tls)
- [Ajustes no .env](#ajustes-no-env)
- [Postgres (opcional)](#postgres-opcional)
- [Construir e subir containers](#construir-e-subir-containers)
- [Migrações e criar usuários](#migrações-e-criar-usuários)
- [Verificações pós-deploy](#verificações-pós-deploy)
- [Healthchecks e systemd (opcional)](#healthchecks-e-systemd-opcional)
- [Backup e manutenção](#backup-e-manutenção)
- [Rollback rápido](#rollback-rápido)
- [Verificações extras de segurança](#verificações-extras-de-segurança)

## Preparar o servidor

Em Ubuntu/Debian (execute como root ou com sudo):

```bash
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg lsb-release
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker $USER
systemctl enable docker --now
```

## Clonar o repositório e preparar arquivos

```bash
cd /srv
git clone https://github.com/Seck1993/PythonAnywhere.git pythonanywhere
cd pythonanywhere
cp .env.example .env
editor .env   # ou use nano/vi
```

## Certificados TLS

Opção A — usar Let's Encrypt com Certbot (recomendado):

```bash
apt install -y certbot
docker compose -f docker-compose.prod.yml down
certbot certonly --standalone -d example.com -d www.example.com
mkdir -p ./certs
cp /etc/letsencrypt/live/example.com/fullchain.pem ./certs/
cp /etc/letsencrypt/live/example.com/privkey.pem ./certs/
```

Opção B — usar certificados próprios: coloque `fullchain.pem` e `privkey.pem` em `./certs`.

## Ajustes no `.env`

- `FLASK_ENV=production`
- `REDIS_URL=redis://redis:6379/0`
- `FORCE_HTTPS=True`
- `SESSION_COOKIE_SECURE=True`
- `REMEMBER_COOKIE_SECURE=True`

### Sobre `.env.example` e segredos

- O arquivo `.env.example` presente no repositório é um template. Mantenha-o no repo para que quem for fazer deploy saiba quais variáveis precisam existir.
- Nunca comite arquivos que contenham segredos reais (por exemplo, um `.env` com `SECRET_KEY` ou senhas). O `.gitignore` já inclui `.env` e `.flaskenv`.
- Em produção prefira um gerenciador de segredos (Vault, AWS Parameter Store, Azure Key Vault, ou GitHub Secrets para CI/CD) em vez de arquivos locais com segredos.
- Para deployments com Docker Compose, copie `.env.example` para `.env` no servidor (fora do repositório) e preencha valores seguros.
- Rotacione e proteja chaves e senhas: troque `SECRET_KEY` e senhas administrativas por valores fortes e troque-os periodicamente.


## Postgres (opcional)

```
DATABASE_URL=postgresql://postgres:senha@postgres:5432/escola
```

## Construir e subir containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

## Migrações e criar usuários

```bash
docker compose -f docker-compose.prod.yml exec web flask db upgrade
docker compose -f docker-compose.prod.yml exec web flask create-super-admin
docker compose -f docker-compose.prod.yml exec web flask create-programmer
```

## Verificações pós-deploy

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml exec web python -c "import redis; print(redis.from_url('redis://redis:6379/0').ping())"
docker compose -f docker-compose.prod.yml logs web | grep "Rate limiter storage"
```

### Testes rápidos HTTP

```bash
curl -I -k https://example.com/
curl -I https://example.com/ | grep -i csp
```

## Healthchecks e systemd (opcional)

Crie um serviço systemd para garantir que o compose suba com o host ou use outra solução de orquestração.

## Backup e manutenção

- Faça backups regulares do banco e do diretório de uploads (`static/uploads`).
- Configure rotação de logs e monitoramento.

## Rollback rápido

```bash
docker compose -f docker-compose.prod.yml down
docker image ls
docker compose -f docker-compose.prod.yml up -d --build
```

## Verificações extras de segurança

- Confirme `SESSION_COOKIE_SECURE=True` em `.env`.
- Confirme HSTS e CSP via `curl -I`.
- Considere WAF e rate-limiting no Nginx.

----

Se quiser, eu posso gerar um `docker-compose.prod.yml` com Postgres/healthchecks ou adicionar um `wsgi.py`.
