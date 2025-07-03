import app.prefastapi # pylint: disable=W0611

import uuid
import asyncio
from functools import wraps, partial
from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Tuple
from http import HTTPStatus
from typing import Any, Callable, cast

from .constant.constant import CONTENT_LENGTH
from .exception.gzpearl_agent_exception import GZPearlBackendException
from .models.backend_model import JSONResponse, JSONResponseBuilder
from .logger.logger import monitor_logger, log_error, init_fast_api_logger, log_info
from .logger.log_context import LogContext
from .pearl_agent import PearlAIAgent
from .handler.wechat_handler import WeChatHandler
from .utils.utils import Watch


API_EXECUTE_TIMEOUT = 30.0

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_fast_api_logger()

# Automatically synchronize the Notion knowledge base to the local vectorstore when the service starts

async def pretty_request(request: Request) -> str:
    url = request.url.path
    request_method = request.method
    body = await request.body()
    return f"{request_method} {url}\n{body.decode('utf-8')}"


@app.exception_handler(GZPearlBackendException)
async def validation_exception_handler(
        request: Request,  # pylint: disable=unused-argument
        error: GZPearlBackendException) -> JSONResponse:
    request_pretty = await pretty_request(request)
    log_error(f'Received payload is invalid with error {str(error)}\n'
              f'{request_pretty}\n'
              f'{str(error)}', error)
    return JSONResponseBuilder.build_err(
        HTTPStatus.BAD_REQUEST,
        f'request body error {str(error)}.')


@app.exception_handler(GZPearlBackendException)
async def jupyter_exception_handler(
        request: Request,  # pylint: disable=unused-argument
        exc: GZPearlBackendException) -> JSONResponse:
    log_error(f'Got a GZPearlBackendException {str(exc)}', exc)
    return JSONResponseBuilder.build_err(
        exc.error_code,
        f'{exc.message}')

@app.exception_handler(Exception)
async def server_exception_handler(
        request: Request,  # pylint: disable=unused-argument
        e: Exception) -> JSONResponse:
    log_error(f'Got an exception {str(e)}', e)
    return JSONResponseBuilder.build_err(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        'Internal Server Error.')

def get_or_create_trace_id(request: Request) -> str:
    headers = request.headers
    trace_id = headers.get('x-gz-trace-id', '')
    if not trace_id:
        trace_id = str(uuid.uuid4())
    # Set trace id here
    LogContext.set_dict({
        'trace_id': trace_id,
    })
    return trace_id

async def get_content_length(request: Request) -> int:
    if CONTENT_LENGTH in request.headers:
        return int(request.headers.get(CONTENT_LENGTH, '0'))
    body = await request.body()
    return len(body)

def get_route_name(request: Request) -> str:
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return "unknown"
    return str(endpoint.__name__)


def set_log_context(path_params: dict[Any, Any], request: Request) -> None:
    trace_id = get_or_create_trace_id(request)
    LogContext.set_dict({
        'trace_id': trace_id
    })

def unset_log_context() -> None:
    LogContext.set_dict({
        'trace_id': ''
    })


@app.middleware("http")
async def interceptor(request: Request, call_next: Any) -> Response:
    watch = Watch()
    get_or_create_trace_id(request)
    request_url = request.url
    method = request.method
    in_content_length = await get_content_length(request)
    client_host = request.client.host if request.client else ''
    client_port = request.client.port if request.client else ''
    header_filter_list = ['signature', 'digest', 'host', 'accept']
    headers = ", ".join([f"{key}={value}" for key, value in request.headers.items() if key not in header_filter_list])

    log_info(f'[telemetry] HTTP Request {method} {request_url} '
             f'content_length={in_content_length} '
             f'host={client_host} '
             f'port={client_port} '
             f'headers=({headers})',
             monitor_logger)

    try:
        response: Response = await call_next(request)
        out_content_length = response.headers.get(CONTENT_LENGTH, '0')
        execution_time = watch.stop()
        # It must be called after the call_next.
        route_name = get_route_name(request)
        set_log_context(request.scope.get("path_params", {}), request)
        log_info(f'[telemetry] HTTP Response {method} {request_url} {response.status_code} '
                 f'content_length={in_content_length}->{out_content_length} '
                 f'route_name={route_name} '
                 f'duration={execution_time:.0f}ms ',
                 monitor_logger)
        return response
    except Exception as e:
        # RequestValidationError and JupyterProxyException won't be caught here.
        execution_time = watch.stop()
        route_name = get_route_name(request)
        set_log_context(request.scope.get("path_params", {}), request)
        log_error(f'[telemetry] HTTP Response {method} {request_url} {HTTPStatus.INTERNAL_SERVER_ERROR.value} '
                  f'content_length={in_content_length}-> '
                  f'route_name={route_name} '
                  f'duration={execution_time:.0f}ms '
                  f'exception={str(e)} ',
                  e=e,
                  jupyter_log=monitor_logger)
        raise e
    finally:
        unset_log_context()


def log_request_response(
        view_func: Callable[..., Any]) -> Any:
    @wraps(view_func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        request: Request = cast(Request,
                                kwargs.get('request'))  # The first argument is always the request object
        set_log_context(kwargs, request)
        loop = asyncio.get_event_loop()
        func = partial(view_func, *args, **kwargs)

        def _exec() -> Any:
            # It will be executed in a thread. So we should set thread context first.
            set_log_context(kwargs, request)
            ret = func()
            unset_log_context()
            return ret

        async def execute_http_request() -> Response:
            return await asyncio.wait_for(
                loop.run_in_executor(global_executor(), _exec),
                timeout=API_EXECUTE_TIMEOUT)

        # lazy init executor to reduce resource usage.
        from .global_var.global_var import global_executor
        try:
            return await execute_http_request()
        except Exception as e:
            log_error(f"Request failed due to {str(e)}", e)
            raise e

    return wrapper

agent = PearlAIAgent()

# Use (user_id, session_id) as key to isolate multiple sessions
chat_history_dict: Dict[Tuple[str, str], List[dict]] = {}

class QARequestPayload(BaseModel):
    question: str
    user_id: str = None
    session_id: str = None

@app.get("/")
@log_request_response
def read_root(request: Request):
    return {"msg": "Yuerhua - GZ backend running."}

@app.post("/chat/qa")
@log_request_response
def chat_qa(request: Request, data: QARequestPayload):
    answer = WeChatHandler.chat_qa(data, chat_history_dict, agent)
    return {"answer": answer}

@app.get("/wechat")
async def wechat_check(
    request: Request, 
    signature: str = Query(...), 
    timestamp: str = Query(...), 
    nonce: str = Query(...), 
    echostr: str = Query(...)):
    return await WeChatHandler.wechat_check(signature, timestamp, nonce, echostr)

@app.post("/wechat")
async def wechat_msg(request: Request):
    return await WeChatHandler.wechat_qa(request)
