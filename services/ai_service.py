import os, json, re
from pathlib import Path
from openai import OpenAI

PROMPT_DIR=Path(__file__).resolve().parent.parent/"prompts"
MODEL=os.getenv("OPENAI_MODEL","gpt-6-sol")

def client():
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("未配置 OPENAI_API_KEY，请在 Render Environment 中添加。")
    return OpenAI(api_key=key)

def _prompt(name):
    return (PROMPT_DIR/name).read_text(encoding="utf-8")

def _call(instruction, payload, web=False):
    tools=[{"type":"web_search"}] if web else None
    kwargs={"model":MODEL,"instructions":instruction,
            "input":[{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]}
    if tools: kwargs["tools"]=tools
    r=client().responses.create(**kwargs)
    text=r.output_text
    # JSON-first contract; fallback keeps raw text visible rather than guessing.
    try:
        return json.loads(text)
    except Exception:
        m=re.search(r'\{.*\}',text,re.S)
        if m:
            try:return json.loads(m.group(0))
            except Exception:pass
    return {"raw_output":text}

def analyze_product(data):
    return _call(_prompt("analyze.txt"), data, web=data.get("product_type")=="电动工具零件" or data.get("use_web",True))

def generate_listing(data):
    return _call(_prompt("generate.txt"), data, web=data.get("use_web",True))

def optimize_listing(data):
    return _call(_prompt("optimize.txt"), data, web=True)

def lookup_part(part_number, data=None):
    payload={"part_number":part_number, **(data or {})}
    return _call(_prompt("part_lookup.txt"), payload, web=True)
