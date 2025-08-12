import yaml
import openai
import requests
import psycopg2
import os
import logging

def load_mcp_config(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def call_api(tool, input_data):
    url = f"{tool['base_url']}{tool['endpoint']}"
    response = requests.get(url, params=input_data)
    return response.json()

def query_postgres(tool):
    conn_info = tool["connection"]
    query = tool["query"]

    conn = psycopg2.connect(
        host=conn_info["host"],
        port=conn_info["port"],
        user=conn_info["user"],
        password=conn_info["password"],
        database=conn_info["database"]
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute(query)
            colnames = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return [dict(zip(colnames, row)) for row in rows]

def build_prompt(mcp, sim_results, historico):
    context = "\n".join(f"- {m}" for m in mcp["context"]["memory"])
    goals = "\n".join(f"- {g}" for g in mcp["context"]["goals"])

    sim_text = "\n\n".join(
        f"### Cenário {i+1} (Selic: {selic}%)\n{result}"
        for i, (selic, result) in enumerate(zip([13.75, 10.0, 8.0], sim_results))
    )

    hist_text = "\n".join(
        f"- {row['ano']}: média rendimento real = {row['media']:.2f}%"
        for row in historico
    )

    return f"""
Você é {mcp['identity']['name']} ({mcp['identity']['role']}).

## Objetivos
{goals}

## Memória do usuário
{context}

## Resultados das simulações (cenários futuros)
{sim_text}

## Histórico de rendimentos reais (últimos 5 anos)
{hist_text}

Com base nesses dados, gere uma recomendação comparando o cenário futuro com o histórico real.
"""

def run_agent():
    logging.info(f"Starting MCP client...")
    mcp = load_mcp_config("./mcp_client/mcp-client.yml")

    api_tool = next(t for t in mcp["tools"] if t["type"] == "openapi")
    db_tool = next(t for t in mcp["tools"] if t["type"] == "postgres")

    selic_values = [13.75, 10.0, 8.0]
    scenarios = []
    for selic in selic_values:
        input_data = {
            "valor_investido": 50000,
            "tipo_indexador": "ipca",
            "vencimento": "2045-01-01",
            "taxa_juros_ano": 6.5,
            "selic_esperada": selic
        }
        result = call_api(api_tool, input_data)
        scenarios.append(result)

    historico = query_postgres(db_tool)

    prompt = build_prompt(mcp, scenarios, historico)

    api_key = os.environ.get("OPENAI_API_KEY", "")
    openai.api_key = api_key

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": mcp["identity"]["persona"]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    print(response.choices[0].message.content)
    
if __name__ == "__main__":
    run_agent()
