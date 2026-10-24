import os, json, uuid, base64, re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from database.models import db, Listing, DataPacket
from services.ai_service import analyze_product, generate_listing, optimize_listing, lookup_part, build_chatgpt_prompt, one_click_listing
from services.import_utils import parse_chatgpt_json, normalize_tags, invalid_tag_reason
from services.listing_rules import apply_policy, validate_tags, validate_description_lengths

load_dotenv()
APP_VERSION = "1.4.4"
app = Flask(__name__)

@app.context_processor
def inject_app_version():
    return {"app_version": APP_VERSION}
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
        apply_policy(result, data)
        validate_description_lengths(result)
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

@app.post("/api/one-click")
def api_one_click():
    data=request.get_json(silent=True) or {}
    old=data.get("mode")=="optimize"
    if old and not str(data.get("title") or "").strip():
        return jsonify({"error":"请输入旧商品标题"}),400
    if not old and not any(str(data.get(k) or "").strip() for k in ("model","product_name","info")):
        return jsonify({"error":"请输入商品型号、名称或资料"}),400
    try:
        result=one_click_listing(data,old=old)
        record=Listing(title=str(result.get("master_title") or data.get("title") or data.get("product_name") or data.get("model") or "未命名商品")[:500],
            product_type="旧商品优化" if old else str(data.get("product_type") or ""),
            brand=str(data.get("brand") or "")[:200],model=str(data.get("model") or result.get("fact_packet",{}).get("part_number") or "")[:200],
            input_data=json.dumps(data,ensure_ascii=False),output_data=json.dumps(result,ensure_ascii=False))
        db.session.add(record);db.session.commit()
        return jsonify({"listing_id":record.id,"version":APP_VERSION})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":str(e)}),422

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
    parsed=None
    if mode in ("generate", "optimize"):
        try:
            parsed=parse_chatgpt_json(output)
        except ValueError as exc:
            return jsonify({"error":str(exc)}),400
        if not isinstance(parsed,dict) or not isinstance(parsed.get("listings"),list) or not parsed["listings"]:
            return jsonify({"error":"缺少完整 listings 数组，请让 ChatGPT 按 Part0–Part8 JSON 模板重新输出"}),400
        required=("part1_title_ru","part2_title_zh","part3_description_ru","part4_description_zh","part5_hashtags","part6_hashtags_zh","part7_packaging_ru","part8_packaging_zh")
        for index,entry in enumerate(parsed["listings"],1):
            if not isinstance(entry,dict) or any(not entry.get(k) for k in required):
                return jsonify({"error":f"第 {index} 个配置缺少 Part1–Part8 字段"}),400
            if not isinstance(entry["part5_hashtags"],list) or len(entry["part5_hashtags"])!=30:
                return jsonify({"error":f"第 {index} 个配置的俄文标签不是30个"}),400
            entry["part5_hashtags"]=normalize_tags(entry["part5_hashtags"], inp.get("part_number") or inp.get("model") or "", inp.get("brand") or "")
            for tag_index, tag in enumerate(entry["part5_hashtags"], 1):
                reason = invalid_tag_reason(tag)
                if reason:
                    return jsonify({"error":f"第 {index} 个配置的第 {tag_index} 个标签 {tag}：{reason}"}),400
        try:
            validate_tags(parsed, inp)
            apply_policy(parsed, inp)
            validate_description_lengths(parsed)
        except ValueError as exc:
            return jsonify({"error":str(exc)}),400
        parsed.setdefault("compatibility_table",[])
        parsed.setdefault("analysis_summary","待核验：请查看文案中的事实来源")
    title=(parsed or {}).get("master_title") or inp.get("title") or inp.get("product_name") or inp.get("model") or inp.get("part_number") or "ChatGPT导入文案"
    row=Listing(title=str(title)[:500],product_type=str(inp.get("product_type") or mode)[:100],
                brand=str(inp.get("brand") or "")[:200],model=str(inp.get("model") or inp.get("part_number") or "")[:200],
                input_data=json.dumps(inp,ensure_ascii=False),output_data=json.dumps(parsed if parsed is not None else {"raw_output":output,"source":"ChatGPT Plus 手动导入"},ensure_ascii=False))
    db.session.add(row);db.session.commit()
    return jsonify({"listing_id":row.id,"message":"已保存到文案库"})

@app.post("/api/data-packet")
def save_data_packet():
    data=request.get_json(silent=True) or {}
    inp=data.get("input_data") or {}
    output=(data.get("output") or "").strip()
    if not isinstance(inp,dict) or not output or len(output)>200000:
        return jsonify({"error":"请填写商品信息并粘贴完整 Data Packet（不超过20万字）"}),400
    model=str(inp.get("model") or inp.get("part_number") or "").strip()
    if not model:return jsonify({"error":"请先填写型号或零件号"}),400
    row=DataPacket.query.filter_by(model=model).order_by(DataPacket.id.desc()).first()
    if row is None:
        row=DataPacket(model=model)
        db.session.add(row)
    row.product_name=str(inp.get("product_name") or "")[:500]
    row.input_data=json.dumps(inp,ensure_ascii=False)
    row.packet_text=output
    row.updated_at=datetime.utcnow()
    db.session.commit()
    return jsonify({"id":row.id,"message":"Data Packet 已保存"})

@app.get("/api/data-packet")
def read_data_packet():
    model=(request.args.get("model") or "").strip()
    if not model:return jsonify({"error":"缺少零件号"}),400
    row=DataPacket.query.filter_by(model=model).order_by(DataPacket.id.desc()).first()
    if not row:return jsonify({"found":False})
    return jsonify({"found":True,"id":row.id,"output":row.packet_text,"updated_at":row.updated_at.isoformat()})

@app.get("/workspace")
def workspace():
    rows=Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template("workspace.html", listings=rows)

@app.delete("/api/listings/<int:listing_id>")
def delete_listing(listing_id):
    row=Listing.query.get_or_404(listing_id)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"deleted":True,"id":listing_id})

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
