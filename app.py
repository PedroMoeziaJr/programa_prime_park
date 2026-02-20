from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import requests
import os

app = Flask(__name__)

# ===========================
# BANCO DE DADOS (CAMINHO ABSOLUTO)
# ===========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "primepark.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"

db = SQLAlchemy(app)

# ===========================
# CONFIGURAÇÃO FOCUS NFS-e
# ===========================
FOCUS_TOKEN = "auZ8OQpPoEnLNMinuuiqZqjTX0m30ehI"
FOCUS_URL = "https://homologacao.focusnfe.com.br/v2/nfse"

# ===========================
# MODELO DO BANCO
# ===========================
class Estadia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10))
    entrada = db.Column(db.DateTime)
    saida = db.Column(db.DateTime, nullable=True)
    meio_pagamento = db.Column(db.String(20), nullable=True)
    valor = db.Column(db.Float, nullable=True)
    nfse_status = db.Column(db.String(50), nullable=True)
    nfse_numero = db.Column(db.String(50), nullable=True)
    nfse_link = db.Column(db.String(200), nullable=True)

# ===========================
# EMITIR NFS-e
# ===========================
def emitir_nfse(placa, valor):
    ref = f"EST-{placa}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    url = f"{FOCUS_URL}?ref={ref}"

    dados = {
        "prestador": {
            "cnpj": "00000000000000",
            "inscricao_municipal": "123456",
            "codigo_municipio": "5300108"
        },
        "tomador": {
            "cpf": "00000000000",
            "nome": "Cliente Estacionamento"
        },
        "servico": {
            "valor_servicos": float(valor),
            "item_lista_servico": "11.01",
            "discriminacao": f"Serviço de estacionamento - placa {placa}"
        }
    }

    r = requests.post(url, json=dados, auth=(FOCUS_TOKEN, ""))

    try:
        return r.status_code, r.json()
    except:
        return r.status_code, {"erro": r.text}

# ===========================
# TELA INICIAL
# ===========================
@app.route("/")
def index():
    return render_template("index.html")

# ===========================
# ENTRADA
# ===========================
@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    if request.method == "POST":
        placa = request.form["placa"]
        return render_template("confirmar_entrada.html", placa=placa)

    return render_template("entrada.html")

# ===========================
# CONFIRMAR ENTRADA
# ===========================
@app.route("/confirmar_entrada", methods=["POST"])
def confirmar_entrada():
    placa = request.form["placa"]

    nova = Estadia(placa=placa, entrada=datetime.now())
    db.session.add(nova)
    db.session.commit()

    return redirect("/")

# ===========================
# SAÍDA
# ===========================
@app.route("/saida", methods=["GET", "POST"])
def saida():
    if request.method == "POST":
        placa = request.form["placa"]
        registro = Estadia.query.filter_by(placa=placa, saida=None).first()

        if not registro:
            return render_template("saida.html", erro="Placa não encontrada no pátio.")

        registro.saida = datetime.now()
        registro.meio_pagamento = "Dinheiro"
        registro.valor = 10.0
        db.session.commit()

        # EMITIR NFS-e
        status, resposta = emitir_nfse(placa, registro.valor)
        print("FOCUS STATUS:", status)
        print("FOCUS RESPOSTA:", resposta)

        try:
            registro.nfse_status = resposta.get("status")
            registro.nfse_numero = resposta.get("numero")
            registro.nfse_link = resposta.get("caminho_xml")
            db.session.commit()
        except:
            pass

        return redirect("/")

    return render_template("saida.html")

# ===========================
# LOGIN DO OPERADOR
# ===========================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        senha = request.form["senha"]
        if senha == "1234":
            return redirect("/admin")
        return render_template("admin_login.html", erro="Senha incorreta.")
    return render_template("admin_login.html")

# ===========================
# RELATÓRIO DO PÁTIO
# ===========================
@app.route("/admin")
def admin():
    registros = Estadia.query.all()
    return render_template("admin_patio.html", registros=registros)

# ===========================
# EXPORTAR PARA EXCEL
# ===========================
@app.route("/exportar_excel")
def exportar_excel():
    registros = Estadia.query.all()

    dados = []
    for r in registros:
        dados.append({
            "Placa": r.placa,
            "Entrada": r.entrada,
            "Saída": r.saida,
            "Tempo Estacionado": str(r.saida - r.entrada) if r.saida else "",
            "Meio de Pagamento": r.meio_pagamento if r.meio_pagamento else "",
            "Valor Pago": r.valor if r.valor else "",
            "Status NFS-e": r.nfse_status if r.nfse_status else "",
            "Número NFS-e": r.nfse_numero if r.nfse_numero else "",
            "Link XML": r.nfse_link if r.nfse_link else ""
        })

    df = pd.DataFrame(dados)
    caminho = "relatorio_prime_park.xlsx"
    df.to_excel(caminho, index=False)

    return send_file(caminho, as_attachment=True)

# ===========================
# INICIAR
# ===========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

