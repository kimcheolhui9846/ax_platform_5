"""백엔드 OpenAPI 스키마를 파일로 내보낸다. 프론트 타입 생성(npm run gen:api)이 이 파일을 읽는다.

사용: uv run --directory backend python scripts/export_openapi.py <출력 경로>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OpenAPI 스키마를 저장했습니다: {out.resolve()}")
