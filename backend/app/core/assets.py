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
    """파일 저장소 계약. put은 새 id를 돌려주고(이미지 형식만), get은 없거나 형식이 틀린 id면 None이다.
    delete는 그 파일을 지운다. 없거나 형식이 틀린 id면 아무 일도 하지 않는다(예외 없음)."""

    def put(self, owner_id: str, data: bytes, mime: str) -> str: ...

    def get(self, asset_id: str) -> Asset | None: ...

    def delete(self, asset_id: str) -> None: ...


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

    def delete(self, asset_id: str) -> None:
        self._assets.pop(asset_id, None)


class LocalAssetStore:
    """폴더 하나에 파일마다 바이트(`{id}.bin`)와 정보(`{id}.json`: 주인·형식)를 둔다. id 형식만 받아 폴더 밖을 읽지 않는다."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._root = root

    def put(self, owner_id: str, data: bytes, mime: str) -> str:
        asset_id = _new_id(mime)
        # 임시 파일에 쓴 뒤 옮겨 반쯤 쓴 파일이 남지 않게 한다. 정보(.json)가 나중이라 .json이 있으면 .bin도 온전하다
        self._write_atomically(self._root / f"{asset_id}.bin", data)
        self._write_atomically(self._root / f"{asset_id}.json", json.dumps({"owner_id": owner_id, "mime": mime}).encode("utf-8"))
        return asset_id

    @staticmethod
    def _write_atomically(path: Path, data: bytes) -> None:
        temp = path.with_name(path.name + ".tmp")
        temp.write_bytes(data)
        temp.replace(path)

    def get(self, asset_id: str) -> Asset | None:
        if not _ASSET_ID.fullmatch(asset_id):
            return None
        try:
            info = json.loads((self._root / f"{asset_id}.json").read_text(encoding="utf-8"))
            return Asset(owner_id=info["owner_id"], mime=info["mime"], data=(self._root / f"{asset_id}.bin").read_bytes())
        except (OSError, ValueError, KeyError):  # 없거나 깨진 파일은 없는 파일과 같다
            return None

    def delete(self, asset_id: str) -> None:
        if not _ASSET_ID.fullmatch(asset_id):
            return
        # 정보(.json)를 먼저 지워 .json이 있으면 .bin도 온전하다는 약속을 지킨다
        (self._root / f"{asset_id}.json").unlink(missing_ok=True)
        (self._root / f"{asset_id}.bin").unlink(missing_ok=True)


def build_asset_store(kind: StoreKind, root: Path) -> AssetStore:
    """세션 저장소(STORE)와 짝을 맞춘다: sqlite면 로컬 폴더(ASSET_DIR), memory면 메모리."""
    return LocalAssetStore(root) if kind == "sqlite" else InMemoryAssetStore()
