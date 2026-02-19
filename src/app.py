"""
Flask API 서버.
실행: 프로젝트 루트에서 python -m src.app 또는 python src/app.py
"""
import os
import html as html_module
from flask import Flask, send_file, send_from_directory, request, Response

# 프로젝트 루트 = src의 상위
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SRC_DIR)
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")

app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path="")
app.json.ensure_ascii = False

# 라우트 등록 전에 config, db, db_logger 임포트 (python src/app.py | python -m src.app 둘 다 지원)
def _import_src():
    try:
        from . import config as c
        from . import db as d
        from . import db_logger as l
        from .routes import api as a
        return c, d, l, a
    except ImportError:
        import config as c
        import db as d
        import db_logger as l
        from routes import api as a
        return c, d, l, a

config_module, db, db_logger, api = _import_src()

app.register_blueprint(api)


def get_db_env_for_display():
    keys = ["PORT", "DB_TYPE", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    out = {}
    for key in keys:
        v = getattr(config_module, key, None)
        if key == "DB_PASSWORD":
            out[key] = "********" if (v is not None and len(str(v)) > 0) else "(미설정)"
        else:
            out[key] = str(v) if (v is not None and v != "") else "(미설정)"
    return out


def escape_html(s):
    if s is None:
        return ""
    return html_module.escape(str(s))


def get_access_denied_html():
    env = get_db_env_for_display()
    rows = "".join(
        f'<tr><th style="text-align:left;padding:0.4rem 0.6rem;border-bottom:1px solid #eee;">{escape_html(k)}</th>'
        f'<td style="padding:0.4rem 0.6rem;border-bottom:1px solid #eee;word-break:break-all;">{escape_html(v)}</td></tr>'
        for k, v in env.items()
    )
    table = f'<table style="width:100%;max-width:400px;margin:1rem auto;font-size:0.9rem;border-collapse:collapse;">{rows}</table>'
    log_entries = db_logger.get_logs()
    if not log_entries:
        log_lines = "(아직 로그 없음)"
    else:
        log_lines = "\n".join(
            f"[{e['time']}] {'ERROR: ' if e.get('isError') else ''}{escape_html(e['msg'])}"
            for e in log_entries
        )
    log_block = f'<pre style="text-align:left;background:#1a1a2e;color:#e2e8f0;padding:1rem;border-radius:6px;font-size:0.8rem;overflow:auto;max-height:200px;">{escape_html(log_lines)}</pre>'
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>접속 불가</title></head>
<body style="font-family:sans-serif;max-width:560px;margin:3rem auto;padding:2rem;text-align:center;">
  <h1 style="color:#dc2626;">접속 불가</h1>
  <p>DB가 설정되지 않았거나 연결되지 않아 서비스를 이용할 수 없습니다.</p>
  <p style="color:#64748b;font-size:0.9rem;">DB_TYPE, DB_HOST, DB_NAME 등 환경 변수를 설정하고 DB 서버가 동작 중인지 확인하세요. (변수·메모리 DB는 사용하지 않습니다.)</p>
  <p style="margin-top:1.5rem;font-size:0.9rem;color:#333;">현재 설정된 환경 변수</p>
  {table}
  <p style="margin-top:1.5rem;font-size:0.9rem;color:#333;">연결 과정 / 디버그 로그</p>
  {log_block}
</body>
</html>"""


@app.route("/ok", methods=["GET"])
def ok():
    return Response("OK", mimetype="text/plain")


@app.route("/gateway-timeout", methods=["GET"])
def gateway_timeout():
    return Response("Gateway Timeout", status=504, mimetype="text/plain")


@app.before_request
def check_db_before_request():
    # /ok, /gateway-timeout 은 DB 검사 생략
    if request.path in ("/ok", "/gateway-timeout"):
        return None
    if not db.is_configured():
        db_logger.add_log("Access denied: DB not configured (DB_TYPE/DB_HOST/DB_NAME or DB_PORT for inference)")
        return Response(
            get_access_denied_html(),
            status=200,
            mimetype="text/html; charset=utf-8",
            headers={"X-Service-Status": "unavailable"},
        )
    if not db.ping():
        db_logger.add_log("Access denied: DB ping failed")
        return Response(
            get_access_denied_html(),
            status=200,
            mimetype="text/html; charset=utf-8",
            headers={"X-Service-Status": "unavailable"},
        )
    return None


@app.route("/", methods=["GET"])
def index():
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return send_file(index_path)
    return Response("index.html not found", status=404)


@app.route("/sample", methods=["GET"])
def sample():
    sample_path = os.path.join(PUBLIC_DIR, "sample.html")
    if os.path.isfile(sample_path):
        return send_file(sample_path)
    return Response("sample.html not found", status=404)


@app.route("/api", methods=["GET"])
def api_info():
    return {
        "message": "API Server",
        "version": "1.0.0",
        "endpoints": {
            "config": "GET /api/config",
            "tables": "GET /api/tables",
            "health": "GET /api/health",
            "items": "GET /api/items",
            "itemsById": "GET /api/items/:id",
        },
    }


@app.errorhandler(500)
def handle_500(err):
    import traceback
    traceback.print_exc()
    return {"error": "Internal Server Error"}, 500


def main():
    if not os.path.isdir(PUBLIC_DIR):
        os.makedirs(PUBLIC_DIR, exist_ok=True)
    port = config_module.PORT
    db_type = db.get_db_type()
    configured = db.is_configured()
    db_logger.add_log(f"Config check: dbType={db_type or '(none)'}, configured={configured}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
