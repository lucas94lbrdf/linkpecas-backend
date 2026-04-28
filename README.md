# 🏎️ LinkPeça - Backend API

O motor por trás do **LinkPeça Marketplace**, um hub inteligente de agregação de ofertas automotivas. Desenvolvido com foco em alta performance, escalabilidade e monitoramento em tempo real.

---

## 🚀 Tecnologias Core

- **FastAPI**: Framework Python de alta performance para APIs modernas.
- **PostgreSQL**: Banco de dados relacional para persistência de dados complexos.
- **Redis**: Cache e gerenciamento de sessões para velocidade máxima.
- **Docker & Docker Compose**: Containerização completa da infraestrutura.
- **Alembic**: Gerenciamento de migrações de banco de dados.

---

## 📊 Stack de Monitoramento

Implementamos uma stack de observabilidade completa para monitorar a saúde do servidor e da aplicação:

- **Prometheus**: Coleta de métricas de performance e uso de recursos.
- **Grafana**: Dashboards visuais (acessíveis via porta `3000`) para análise de dados.
- **Node Exporter**: Monitoramento a nível de hardware do servidor (CPU, Memória, Disco).

---

## 🛠️ Como Rodar o Projeto

### Pré-requisitos
- Docker e Docker Compose instalados.
- Arquivo `.env` configurado na raiz da pasta `/backend`.

### Execução via Docker Compose
Para subir toda a infraestrutura (API, Banco, Redis e Monitoramento) com um único comando:

```bash
docker-compose up -d --build
```

A API estará disponível em: `http://localhost:8000`
A documentação interativa (Swagger) em: `http://localhost:8000/docs`

---

## 🔄 CI/CD e Deploy Automático

O projeto utiliza **GitHub Actions** para automação de deploy. Toda vez que um commit é enviado para a branch `main`:

1.  O GitHub Actions se conecta ao servidor na **GCP** via SSH.
2.  Realiza o `git pull` do código mais recente.
3.  Reinicia os containers via `docker-compose`, garantindo que a versão mais nova esteja sempre online sem intervenção manual.

---

## 🔐 Configurações (.env)

Certifique-se de configurar as seguintes variáveis no seu arquivo `.env`:

```env
# Banco de Dados
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha
POSTGRES_DB=linkpecas_db
DATABASE_URL=postgresql://seu_usuario:sua_senha@postgres:5432/linkpecas_db

# Segurança
SECRET_KEY=sua_chave_secreta_jwt
ALGORITHM=HS256

# Integrações (Opcional)
RESEND_API_KEY=re_xxxxxxxx
```

---

## 📁 Estrutura de Pastas

- `/app`: Código fonte da aplicação (rotas, modelos, esquemas).
- `/alembic`: Scripts de migração de banco de dados.
- `/tests`: Testes automatizados.
- `docker-compose.yml`: Definição de todos os serviços da stack.
- `prometheus.yml`: Configurações de coleta de métricas.
