"""결과 이미지 파일 저장소(메모리·로컬 폴더)와 GET /assets/{id}. 남의 파일·없는 파일은 404다."""
import pytest

from app.core.assets import IMAGE_MIMES, InMemoryAssetStore, LocalAssetStore, UnsupportedAssetType
from app.core.messages import ASSET_NOT_FOUND_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import CLIENT_ID, OTHER_CLIENT_ID, api_client

PNG = bytes([0x89]) + b"PNG"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'


@pytest.fixture(params=["memory", "local"])
def assets(request, tmp_path):
    return InMemoryAssetStore() if request.param == "memory" else LocalAssetStore(tmp_path / "assets")


def test_put_then_get_returns_the_owner_mime_and_bytes(assets):
    asset_id = assets.put("owner-0001", SVG, "image/svg+xml")

    found = assets.get(asset_id)

    assert (found.owner_id, found.mime, found.data) == ("owner-0001", "image/svg+xml", SVG)
    assert asset_id.startswith("asset_")
    assert assets.put("owner-0001", SVG, "image/svg+xml") != asset_id  # 매번 새 id


def test_missing_or_malformed_ids_are_none(assets):
    assert assets.get("asset_" + "0" * 32) is None
    assert assets.get("../sessions.db") is None  # 폴더 밖 경로는 id가 아니다


def test_only_image_types_are_stored(assets):
    assert "image/svg+xml" in IMAGE_MIMES
    with pytest.raises(UnsupportedAssetType):
        assets.put("owner-0001", b"<html>", "text/html")


def test_local_store_survives_a_new_instance(tmp_path):
    asset_id = LocalAssetStore(tmp_path / "assets").put("owner-0001", SVG, "image/svg+xml")
    assert LocalAssetStore(tmp_path / "assets").get(asset_id).data == SVG


def test_get_asset_api_serves_only_the_owner():
    store = InMemoryAssetStore()
    asset_id = store.put(CLIENT_ID, SVG, "image/svg+xml")
    app = create_app(provider=MockProvider(), assets=store)

    mine = api_client(app).get(f"/api/v1/coaching/assets/{asset_id}")
    theirs = api_client(app, client_id=OTHER_CLIENT_ID).get(f"/api/v1/coaching/assets/{asset_id}")
    missing = api_client(app).get("/api/v1/coaching/assets/asset_" + "f" * 32)

    assert mine.status_code == 200
    assert mine.content == SVG
    assert mine.headers["content-type"].startswith("image/svg+xml")
    assert mine.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in mine.headers["content-security-policy"]
    assert (theirs.status_code, theirs.json()) == (404, {"detail": ASSET_NOT_FOUND_MESSAGE})
    assert (missing.status_code, missing.json()) == (404, {"detail": ASSET_NOT_FOUND_MESSAGE})
    assert api_client(app, client_id=None).get(f"/api/v1/coaching/assets/{asset_id}").status_code == 422


def test_asset_route_documents_image_bodies_and_errors():
    spec = api_client(create_app(provider=MockProvider())).get("/openapi.json").json()
    responses = spec["paths"]["/api/v1/coaching/assets/{asset_id}"]["get"]["responses"]
    assert set(responses["200"]["content"]) == set(IMAGE_MIMES)
    assert {"404", "422", "500"} <= set(responses)


def test_get_asset_api_forbids_shared_caches_and_keeps_the_stored_mime():
    store = InMemoryAssetStore()
    asset_id = store.put(CLIENT_ID, PNG, "image/png")
    app = create_app(provider=MockProvider(), assets=store)

    response = api_client(app).get(f"/api/v1/coaching/assets/{asset_id}")

    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, no-store"


def test_local_store_returns_none_for_missing_or_broken_files(tmp_path):
    store = LocalAssetStore(tmp_path / "assets")
    asset_id = store.put("owner-0001", SVG, "image/svg+xml")
    (tmp_path / "assets" / f"{asset_id}.bin").unlink()
    assert store.get(asset_id) is None  # 바이트 파일이 없다

    other = store.put("owner-0001", SVG, "image/svg+xml")
    (tmp_path / "assets" / f"{other}.json").write_text("{깨짐", encoding="utf-8")
    assert store.get(other) is None  # 정보 파일이 깨졌다

    third = store.put("owner-0001", SVG, "image/svg+xml")
    (tmp_path / "assets" / f"{third}.json").write_text("{}", encoding="utf-8")
    assert store.get(third) is None  # 키가 빠졌다


def test_local_store_leaves_no_temp_files(tmp_path):
    store = LocalAssetStore(tmp_path / "assets")
    asset_id = store.put("owner-0001", SVG, "image/svg+xml")
    assert sorted(p.name for p in (tmp_path / "assets").iterdir()) == [f"{asset_id}.bin", f"{asset_id}.json"]
