from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import math
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "prime_park.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==========================
# MODELO
# ==========================

class Estadia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), nullable=False)
    entrada = db.Column(db.DateTime, nullable=False)
    saida = db.Column(db.DateTime, nullable=True)
    valor = db.Column(db.Float, nullable=True)
    pago = db.Column(db.Boolean, default=False)

    def calcular_valor(self):
        if not self.saida:
            return 0.0

        minutos = (self.saida - self.entrada).total_seconds() / 60
        horas = math.ceil(minutos / 60)

        if horas <= 1:
            return 5.0
        else:
            return 5.0 + (horas - 1) * 3.0


# ==========================
# ROTAS
# ==========================

@app.before_first_request
def criar_banco():
    db.create_all()

@app.route("/")
def index():
    abertas = Estadia.query.filter_by(pago=False, saida=None).all()
    return render_template("index.html", abertas=abertas)

@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    if request.method == "POST":
        placa = request.form["placa"].upper().strip()
        if not placa:
            return redirect(url_for("entrada"))

        agora = datetime.now()
        estadia = Estadia(placa=placa, entrada=agora)
        db.session.add(estadia)
        db.session.commit()

        return render_template("ticket_entrada.html", placa=placa, entrada=agora)

    return render_template("entrada.html")

@app.route("/saida", methods=["GET", "POST"])
def saida():
    if request.method == "POST":
        placa = request.form["placa"].upper().strip()
        estadia = Estadia.query.filter_by(placa=placa, pago=False, saida=None).first()

        if not estadia:
            return render_template("saida.html", erro="Placa não encontrada ou já finalizada.")

        estadia.saida = datetime.now()
        valor = estadia.calcular_valor()
        estadia.valor = valor
        db.session.commit()

        return render_template(
            "pagamento.html",
            placa=estadia.placa,
            entrada=estadia.entrada,
            saida=estadia.saida,
            valor=valor,
            id=estadia.id
        )

    return render_template("saida.html")

@app.route("/pagar/<int:id>", methods=["POST"])
def pagar(id):
    estadia = Estadia.query.get_or_404(id)
    estadia.pago = True
    db.session.commit()

    return render_template(
        "ticket_saida.html",
        placa=estadia.placa,
        entrada=estadia.entrada,
        saida=estadia.saida,
        valor=estadia.valor
    )

if __name__ == "__main__":
    app.run(debug=True)
