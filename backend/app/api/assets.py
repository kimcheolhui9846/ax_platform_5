"""결과 이미지 파일 내려주기. 브라우저 <img>는 X-Client-Id를 못 보내므로 프론트가 헤더를 붙여 받아 data URL로 쓴다."""
from fastapi import APIRouter, HTTPException, Response

from app.api.deps import Assets, Owner
from app.api.responses import error_responses
from app.core.assets import IMAGE_MIMES
from app.core.messages import ASSET_NOT_FOUND_MESSAGE

router = APIRouter(prefix="/api/v1/coaching", tags=["assets"], responses=error_responses(500))

# SVG를 주소로 바로 열어도 스크립트·외부 자원이 돌지 않게 한다
_SAFE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
}


@router.get(
    "/assets/{asset_id}",
    response_class=Response,
    responses={
        200: {
            "description": "이미지 바이트",
            "content": {mime: {"schema": {"type": "string", "format": "binary"}} for mime in sorted(IMAGE_MIMES)},
        },
        **error_responses(404, 422),
    },
)
def get_asset(asset_id: str, assets: Assets, owner: Owner) -> Response:
    """남의 파일은 없는 파일과 같은 404다."""
    asset = assets.get(asset_id)
    if asset is None or asset.owner_id != owner:
        raise HTTPException(status_code=404, detail=ASSET_NOT_FOUND_MESSAGE)
    return Response(content=asset.data, media_type=asset.mime, headers=_SAFE_HEADERS)
