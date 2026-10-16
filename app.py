import os, json, uuid, base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from database.models import db, Listing
from services.ai_service import analyze_product, generate_listing, optimize_listing, lookup_part, build_chatgpt_prompt

load_dotenv()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///ozon_listing.db").replace("postgres://","postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.get("/")
def index():
    recent = Listing.query.order_by(Listing.created_at.desc()).limit(10).all()
    return render_template("index.html", recent=recent)

@app.get("/new")
def new_product():
    return render_template("new_product.html")

@app.post("/api/analyze")
def api_analyze():
    data = request.get_json(force=True)
    try:
        result = analyze_product(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/api/generate")
def api_generate():
    data = request.get_json(force=True)
    try:
        result = generate_listing(data)
        record = Listing(
            title=result.get("master_title") or data.get("model") or data.get("product_name") or "未命名商品",
            product_type=data.get("product_type",""),
            brand=data.get("brand",""),
            model=data.get("model",""),
            input_data=json.dumps(data, ensure_ascii=False),
            output_data=json.dumps(result, ensure_ascii=False),
        )
        db.session.add(record); db.session.commit()
        result["listing_id"] = record.id
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/optimize")
def optimize_page():
    return render_template("optimize.html")

@app.post("/api/optimize")
def api_optimize():
    data=request.get_json(force=True)
    try:
        result=optimize_listing(data)
        record=Listing(
            title=result.get("title") or "旧商品优化",
            product_type="旧商品优化",
            brand=data.get("brand",""),
            model=data.get("model",""),
            input_data=json.dumps(data, ensure_ascii=False),
            output_data=json.dumps(result, ensure_ascii=False),
        )
        db.session.add(record); db.session.commit()
        result["listing_id"]=record.id
        return jsonify(result)
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.get("/parts")
def parts():
    return render_template("part_lookup.html")

@app.post("/api/part-lookup")
def api_part_lookup():
    data=request.get_json(force=True)
    try:
        return jsonify(lookup_part(data.get("part_number",""), data))
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.post("/api/chatgpt-prompt")
def chatgpt_prompt():
    data=request.get_json(force=True) or {}
    mode=data.get("mode", "analyze")
    if mode not in ("analyze", "generate", "optimize", "part_lookup"):
        return jsonify({"error":"不支持的模式"}),400
    return jsonify({"prompt":build_chatgpt_prompt(mode,data)})

@app.post("/api/import-listing")
def import_listing():
    data=request.get_json(force=True) or {}
    output=(data.get("output") or "").strip()
    if not output:
        return jsonify({"error":"请先粘贴 ChatGPT 结果"}),400
    if len(output)>200000:
        return jsonify({"error":"内容过长"}),400
    inp=data.get("input_data") or {}
    if not isinstance(inp,dict):
        return jsonify({"error":"商品数据格式错误"}),400
    mode=data.get("mode") or "generate"
    title=(inp.get("product_name") or inp.get("model") or inp.get("part_number") or "ChatGPT导入文案")[:500]
    row=Listing(title=title,product_type=str(inp.get("product_type") or mode)[:100],
                brand=str(inp.get("brand") or "")[:200],model=str(inp.get("model") or inp.get("part_number") or "")[:200],
                input_data=json.dumps(inp,ensure_ascii=False),output_data=json.dumps({"raw_output":output,"source":"ChatGPT Plus 手动导入"},ensure_ascii=False))
    db.session.add(row);db.session.commit()
    return jsonify({"listing_id":row.id,"message":"已保存到文案库"})

@app.get("/workspace")
def workspace():
    rows=Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template("workspace.html", listings=rows)

@app.get("/api/listings/<int:listing_id>")
def get_listing(listing_id):
    row=Listing.query.get_or_404(listing_id)
    return jsonify({
        "id":row.id, "title":row.title, "product_type":row.product_type,
        "brand":row.brand, "model":row.model,
        "input_data":json.loads(row.input_data or "{}"),
        "output_data":json.loads(row.output_data or "{}"),
        "created_at":row.created_at.isoformat()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=os.getenv("FLASK_DEBUG","0")=="1")
