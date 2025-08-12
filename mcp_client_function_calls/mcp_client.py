import yaml
import openai
import requests
import psycopg2
import os
import logging
import json

def load_mcp_config(path: str):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def call_api(valor_investido, tipo_indexador, vencimento, taxa_juros_ano, selic_esperada, tool):
    url = f"{tool['base_url']}{tool['endpoint']}"
    params = {
        "valor_investido": valor_investido,
        "tipo_indexador": tipo_indexador,
        "vencimento": vencimento,
        "taxa_juros_ano": taxa_juros_ano,
        "selic_esperada": selic_esperada
    }
    response = requests.get(url, params=params)
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

def run_agent():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting MCP client...")

    mcp = load_mcp_config("./mcp_client/mcp-client.yml")
    api_tool = next(t for t in mcp["tools"] if t["type"] == "openapi")
    db_tool = next(t for t in mcp["tools"] if t["type"] == "postgres")

    # Define OpenAI tools (function schemas)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "simular_investimento",
                "description": "Simula investimento com parâmetros fornecidos",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "valor_investido": {"type": "number"},
                        "tipo_indexador": {"type": "string"},
                        "vencimento": {"type": "string"},
                        "taxa_juros_ano": {"type": "number"},
                        "selic_esperada": {"type": "number"}
                    },
                    "required": [
                        "valor_investido", "tipo_indexador", "vencimento", "taxa_juros_ano", "selic_esperada"
                    ]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_historico_rendimento",
                "description": "Consulta o histórico de rendimento real dos últimos 5 anos",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

    # Mensagem inicial
    context = "\n".join(f"- {m}" for m in mcp["context"]["memory"])
    goals = "\n".join(f"- {g}" for g in mcp["context"]["goals"])
    system_prompt = f"""
Você é {mcp['identity']['name']} ({mcp['identity']['role']}).
## Objetivos
{goals}
## Memória do usuário
{context}
"""

    api_key = os.environ.get("OPENAI_API_KEY", "")
    client = openai.OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": mcp["identity"]["persona"]},
        {"role": "user", "content": system_prompt + "Simule cenários futuros e compare com o histórico real."}
    ]

    # Primeira chamada: modelo pode pedir simulação e histórico
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = response.choices[0].message

    # Executa as tools solicitadas pelo modelo
    tool_outputs = {}
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "simular_investimento":
                args = json.loads(tool_call.function.arguments)
                result = call_api(**args, tool=api_tool)
                tool_outputs[tool_call.id] = result
            elif tool_call.function.name == "consultar_historico_rendimento":
                result = query_postgres(db_tool)
                tool_outputs[tool_call.id] = result
                messages_followup = [
                    {"role": "system", "content": mcp["identity"]["persona"]},
                    {"role": "user", "content": system_prompt + "Simule cenários futuros e compare com o histórico real."},
                    {
                        "role": "assistant",
                        "tool_calls": msg.tool_calls,
                        "content": None  # ou "" se preferir
                    },
                ]
                for tool_call in msg.tool_calls:
                    messages_followup.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_outputs[tool_call.id], default=str)
                    })

                # Agora sim, faça a segunda chamada:
                followup = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_followup
                )
                print(followup.choices[0].message.content)
    else:
        print(msg.content)

if __name__ == "__main__":
    run_agent()