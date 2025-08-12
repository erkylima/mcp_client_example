from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/simular", methods=["GET"])
def simular():
    valor = float(request.args.get("valor_investido"))
    taxa = float(request.args.get("taxa_juros_ano"))
    selic = float(request.args.get("selic_esperada"))
    anos = 2045 - 2025

    rendimento = valor * ((1 + (taxa + (15 - selic)/10)/100) ** anos)
    return jsonify({
        "valor_investido": valor,
        "taxa": taxa,
        "selic": selic,
        "vencimento": "2045",
        "rendimento_estimado": round(rendimento, 2)
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
