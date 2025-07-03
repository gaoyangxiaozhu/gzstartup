from starlette.responses import Response
import json
from http import HTTPStatus
from pydantic import BaseModel

from typing import Any

class JSONResponse(Response):
    def __init__(
            self,
            content: Any,
            status_code: int = 200
    ) -> None:
        super().__init__(content, status_code, None, "application/json", None)

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

class JSONResponseBuilder(BaseModel):
    @classmethod
    def build_err(cls, code: int, msg: str) -> JSONResponse:
        return JSONResponse(
            content={
                'errorMsg': msg
            },
            status_code=code
        )

    @classmethod
    def build_ok(cls) -> JSONResponse:
        return JSONResponse(
            content={
                'errorMsg': ''
            },
            status_code=HTTPStatus.OK
        )

    @classmethod
    def build(cls, code: int, body: Any) -> JSONResponse:
        return JSONResponse(
            content=body,
            status_code=code
        )