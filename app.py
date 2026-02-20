from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import math
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "prime_park.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "prime_park_secret"

db = SQLAlchemy(app)


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


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    if request.method == "POST":
        placa = request.form.get("placa", "").upper().strip()
        if not placa:
            return redirect(url_for("entrada"))
        return redirect(url_for("confirmar_entrada", placa=placa))
    return render_template("entrada.html")


@app.route("/confirmar_entrada")
def confirmar_entrada():
    placa = request.args.get("placa", "").upper().strip()
    if not placa:
        return redirect(url_for("entrada"))
    return render_template("confirmar_entrada.html", placa=placa)


@app.route("/confirmar_entrada_ok", methods=["POST"])
def confirmar_entrada_ok():
    placa = request.form.get("placa", "").upper().strip()
    if not placa:
        return redirect(url_for("entrada"))

    agora = datetime.now()
    estadia = Estadia(placa=placa, entrada=agora)
    db.session.add(estadia)
    db.session.commit()

    return render_template("ticket_entrada.html", placa=placa, entrada=agora)


@app.route("/saida", methods=["GET", "POST"])
def saida():
    if request.method == "POST":
        placa = request.form.get("placa", "").upper().strip()
        if not placa:
            return redirect(url_for("saida"))
        return redirect(url_for("confirmar_saida", placa=placa))
    return render_template("saida.html", erro=None)


@app.route("/confirmar_saida")
def confirmar_saida():
    placa = request.args.get("placa", "").upper().strip()
    if not placa:
        return redirect(url_for("saida"))

    estadia = Estadia.query.filter_by(placa=placa, pago=False, saida=None).first()
    if not estadia:
        return render_template("saida.html", erro="Placa não encontrada ou já finalizada.")

    agora = datetime.now()
    estadia.saida = agora
    valor = estadia.calcular_valor()
    estadia.valor = valor
    db.session.commit()

    return render_template(
        "confirmar_saida.html",
        placa=estadia.placa,
        entrada=estadia.entrada,
        saida=estadia.saida,
        valor=valor,
        id=estadia.id
    )


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


@app.route("/admin")
def admin():
    return render_template("admin_login.html", erro=None)


@app.route("/admin_login", methods=["POST"])
def admin_login():
    senha = request.form.get("senha", "")
    if senha == "1234":
        return redirect(url_for("admin_patio"))
    return render_template("admin_login.html", erro="Senha incorreta.")


@app.route("/admin_patio")
def admin_patio():
    abertas = Estadia.query.filter_by(pago=False, saida=None).all()
    return render_template("admin_patio.html", abertas=abertas)


@app.route("/admin_remover/<int:id>", methods=["POST"])
def admin_remover(id):
    estadia = Estadia.query.get_or_404(id)
    db.session.delete(estadia)
    db.session.commit()
    return redirect(url_for("admin_patio"))


if __name__ == "__main__":
    app.run(debug=True)
