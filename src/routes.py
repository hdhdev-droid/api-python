"""API 라우트: /api/config, /api/tables, /api/health, /api/items."""
from datetime import datetime
from flask import Blueprint, jsonify, request
try:
    from . import config as config_module
    from . import db
except ImportError:
    import config as config_module
    import db

api = Blueprint("api", __name__, url_prefix="/api")


def get_db_env_for_display():
    keys = ["DB_TYPE", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    out = {}
    for key in keys:
        v = getattr(config_module, key, None)
        if key == "DB_PASSWORD":
            out[key] = "********" if (v is not None and len(str(v)) > 0) else "(미설정)"
        else:
            out[key] = str(v) if (v is not None and v != "") else "(미설정)"
    return out


@api.route("/config", methods=["GET"])
def config():
    return jsonify(env=get_db_env_for_display())


@api.route("/tables", methods=["GET"])
def tables():
    try:
        result = db.get_tables()
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e) or "서버 오류"), 500


@api.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok", timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")


@api.route("/items", methods=["GET"])
def get_items():
    try:
        items = db.get_items()
        if items is None or not isinstance(items, list):
            return jsonify(error="DB 연결을 사용할 수 없습니다. 아이템은 DB에서만 조회됩니다."), 503
        return jsonify(items)
    except Exception as e:
        return jsonify(error=str(e)), 500


@api.route("/items/<int:id>", methods=["GET"])
def get_item_by_id(id):
    try:
        item = db.get_item_by_id(id)
        if not item:
            return jsonify(error="Not found"), 404
        return jsonify(item)
    except Exception as e:
        return jsonify(error=str(e)), 500


@api.route("/items", methods=["POST"])
def create_item():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify(error="name is required"), 400
    try:
        new_item = db.create_item(name)
        if new_item is None:
            return jsonify(error="DB 연결을 사용할 수 없습니다. 아이템은 DB에만 저장됩니다."), 503
        return jsonify(new_item), 201
    except Exception as e:
        return jsonify(error=str(e)), 500
