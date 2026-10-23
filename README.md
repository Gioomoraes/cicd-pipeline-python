# cicd-pipeline-python

 Pipeline de CI/CD construído com GitHub Actions para uma API Python simples. A cada push, o código passa por lint, testes e verificações de segurança, é empacotado em uma imagem Docker que é escaneada e publicada, e em seguida é implantado em staging e produção (simulados), com aprovação manual antes da produção.


## Conjunto de tecnolgias

Python 3.11/3.12, FastAPI, pytest, ruff, Docker, GitHub Actions, GitHub Container Registry, Trivy, bandit, pip-audit, gitleaks, Dependabot.


## Layout do repositório

```
.
├── .github/workflows/     
├── .github/dependabot.yml
├── .kiro/steering/        
├── app/                  
├── tests/                 
├── k8s/                  
├── scripts/               
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Execute localmente

```bash
python -m venv .venv
source .venv/bin/activate         
pip install -e ".[dev]"

ruff check .
ruff format --check .
pytest --cov=app --cov-fail-under=80

APP_VERSION=dev uvicorn app.main:app --port 8000
```

Em outro terminal, execute o mesmo teste de fumaça usado no gasoduto:

```bash
python scripts/smoke_test.py --url http://localhost:8000 --expected-version dev
```

Com Docker instalado:

```bash
docker compose up
```

## Autora - Giovanna de Moraes 💜

