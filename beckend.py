from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== MODELS =====

class ContaCreate(BaseModel):
    nome: str
    saldo: float

class TransacaoCreate(BaseModel):
    origem: int
    destino: int
    valor: float

# ===== BANCO =====

contas = []
transacoes = []
alertas = []
proximo_id = 1


# ===== FRAUDE AUTOMÁTICA =====

def verificar_fraude_automatica():

    agora = time.time()
    motivos = []

    # Limpa alertas antigos (30s)
    global alertas
    alertas = [a for a in alertas if agora - a["timestamp"] < 30]

    # Regra 1: muitas transações
    if len(transacoes) > 5:
        motivos.append("Muitas transações")

    # Regra 2: valor alto
    for t in transacoes:
        if t["valor"] > 10000:
            motivos.append("Valor muito alto")
            break

    # Regra 3: frequência (últimos 10s)
    recentes = [t for t in transacoes if agora - t["timestamp"] < 10]
    if len(recentes) >= 3:
        motivos.append("Muitas transações em pouco tempo")

    # Regra 4: mesma conta enviando muito
    contagem = {}
    for t in transacoes:
        contagem[t["origem"]] = contagem.get(t["origem"], 0) + 1

    for conta, qtd in contagem.items():
        if qtd >= 3:
            motivos.append(f"Conta {conta} muito ativa")
            break

    if motivos:
        alerta = {
            "fraude": True,
            "motivos": motivos,
            "timestamp": agora
        }
        alertas.append(alerta)


# ===== ROTAS =====

@app.get("/")
def home():
    return {"mensagem": "Banco rodando com antifraude automático 🔥"}


@app.get("/contas")
def listar_contas():
    return contas


@app.post("/contas")
def criar_conta(dados: ContaCreate):
    global proximo_id

    if dados.saldo < 0:
        raise HTTPException(status_code=400, detail="Saldo inválido")

    conta = {
        "id": proximo_id,
        "nome": dados.nome,
        "saldo": dados.saldo
    }

    contas.append(conta)
    proximo_id += 1

    return conta


@app.post("/transacao")
def criar_transacao(dados: TransacaoCreate):

    origem = next((c for c in contas if c["id"] == dados.origem), None)
    destino = next((c for c in contas if c["id"] == dados.destino), None)

    if not origem or not destino:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if dados.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor inválido")

    if origem["saldo"] < dados.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")

    origem["saldo"] -= dados.valor
    destino["saldo"] += dados.valor

    transacao = {
        "origem": dados.origem,
        "destino": dados.destino,
        "valor": dados.valor,
        "timestamp": time.time()
    }

    transacoes.append(transacao)

    # 🚨 chama antifraude automático
    verificar_fraude_automatica()

    return {"status": "Transação realizada"}


@app.get("/transacoes")
def listar_transacoes():
    return transacoes


# ===== ALERTAS (tempo real via polling) =====

@app.get("/alertas")
def listar_alertas():
    agora = time.time()
    # só retorna alertas recentes (30s)
    return [a for a in alertas if agora - a["timestamp"] < 30]
