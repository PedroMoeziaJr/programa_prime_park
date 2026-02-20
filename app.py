from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///primepark.db"
db = SQLAlchemy(app)

# ===========================
# BANCO DE DADOS
# ===========================
class Estadia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10))
    entrada = db.Column(db.DateTime)
    saida = db.Column(db.DateTime, nullable=True)
    meio_pagamento = db.Column(db.String(20), nullable=True)
    valor = db.Column(db.Float, nullable=True)

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
        nova = Estadia(placa=placa, entrada=datetime.now())
        db.session.add(nova)
        db.session.commit()
        return redirect("/")
    return render_template("entrada.html")

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
            "Valor Pago": r.valor if r.valor else ""
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
