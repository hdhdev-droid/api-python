# API Server (Python)

Node.js [api-server](https://github.com/...) 데모를 Python(Flask)으로 마이그레이션한 API 서버입니다.

## 요구 사항

- Python 3.10+
- DB: PostgreSQL / MySQL·MariaDB / MongoDB 중 하나 (환경 변수로 지정)

## 설치 및 실행

```bash
# 가상환경 권장
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
cp .env.example .env     # 필요 시 .env 수정 (PORT, DB_*)
python src/app.py
```

또는 프로젝트 루트에서:

```bash
python -m src.app
```

서버는 기본적으로 `http://0.0.0.0:81` 에서 동작합니다. `.env` 의 `PORT` 또는 `WEB_PORT` 로 변경 가능합니다.

## 환경 변수 (.env)

| 변수 | 설명 |
|------|------|
| `PORT` / `WEB_PORT` | 서버 포트 (기본 81) |
| `DB_TYPE` | `POSTGRESQL` \| `MYSQL` \| `MARIADB` \| `MONGODB` (생략 시 `DB_PORT`로 추론) |
| `DB_HOST` | DB 호스트 |
| `DB_PORT` | DB 포트 (5432 / 3306 / 27017 등) |
| `DB_NAME` | DB 이름 |
| `DB_USER` | DB 사용자 |
| `DB_PASSWORD` | DB 비밀번호 |

## 엔드포인트

- `GET /ok` — 헬스 체크 (텍스트 "OK")
- `GET /gateway-timeout` — 504 테스트
- `GET /` — 메인 페이지 (DB 테이블 목록)
- `GET /sample` — 샘플 API 테스트 페이지
- `GET /api` — API 정보
- `GET /api/config` — DB 환경 변수 (비밀번호 마스킹)
- `GET /api/tables` — DB 테이블 목록
- `GET /api/health` — 상태·타임스탬프
- `GET /api/items` — 아이템 목록
- `GET /api/items/:id` — 아이템 단건
- `POST /api/items` — 아이템 추가 (body: `{"name": "..."}`)

DB가 설정되지 않았거나 연결에 실패하면, `/ok`, `/gateway-timeout` 을 제외한 요청에서 "접속 불가" HTML이 반환됩니다.
