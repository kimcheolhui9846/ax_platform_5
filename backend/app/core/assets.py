"""결과 이미지 같은 파일의 저장소. 메모리(테스트)와 로컬 폴더(서버를 다시 켜도 남는다) 두 가지다.

세션 JSON에는 파일 id만 두고 바이트는 여기에 둔다. 주인(owner_id)을 함께 적어 내려줄 때 검사한다.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.core.store import StoreKind

IMAGE_MIMES = frozenset({"image/svg+xml", "image/png", "image/jpeg", "image/webp"})
_ASSET_ID = re.compile(r"asset_[0-9a-f]{32}")


class UnsupportedAssetType(ValueError):
    """이미지가 아닌 형식이다(제공자 구현 오류)."""


@dataclass(frozen=True)
class Asset:
    owner_id: str
    mime: str
    data: bytes


class AssetStore(Protocol):
    """파일 저장소 계약. put은 새 id를 돌려주고(이미지 형식만), get은 없거나 형식이 틀린 id면 None이다."""

    def put(self, owner_id: str, data: bytes, mime: str) -> str: ...

    def get(self, asset_id: str) -> Asset | None: ...


def _new_id(mime: str) -> str:
    if mime not in IMAGE_MIMES:
        raise UnsupportedAssetType(f"이미지가 아닌 형식입니다: {mime}")
    return f"asset_{uuid4().hex}"


class InMemoryAssetStore:
    """서버를 재시작하면 사라진다. 테스트의 기본값이다."""

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def put(self, owner_id: str, data: bytes, mime: str) -> str:
        asset_id = _new_id(mime)
        self._assets[asset_id] = Asset(owner_id=owner_id, mime=mime, data=data)
        return asset_id

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)


class LocalAssetStore:
    """폴더 하나에 파일마다 바이트(`{id}.bin`)와 정보(`{id}.json`: 주인·형식)를 둔다. id 형식만 받아 폴더 밖을 읽지 않는다."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._root = root

    def put(self, owner_id: str, data: bytes, mime: str) -> str:
        asset_id = _new_id(mime)
        (self._root / f"{asset_id}.bin").write_bytes(data)
        (self._root / f"{asset_id}.json").write_text(json.dumps({"owner_id": owner_id, "mime": mime}), encoding="utf-8")
        return asset_id

    def get(self, asset_id: str) -> Asset | None:
        if not _ASSET_ID.fullmatch(asset_id):
            return None
        meta = self._root / f"{asset_id}.json"
        if not meta.exists():
            return None
        info = json.loads(meta.read_text(encoding="utf-8"))
        return Asset(owner_id=info["owner_id"], mime=info["mime"], data=(self._root / f"{asset_id}.bin").read_bytes())


def build_asset_store(kind: StoreKind, root: Path) -> AssetStore:
    """세션 저장소(STORE)와 짝을 맞춘다: sqlite면 로컬 폴더(ASSET_DIR), memory면 메모리."""
    return LocalAssetStore(root) if kind == "sqlite" else InMemoryAssetStore()
