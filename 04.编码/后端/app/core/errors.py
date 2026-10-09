from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException
import logging


class APIError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status


def ok(data=None, message='success'):
    return {'code': 0, 'message': message, 'data': data}


def install_handlers(app):
    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={'code': 2002 if exc.status_code == 404 else 2001,
                            'message': '接口不存在' if exc.status_code == 404 else str(exc.detail), 'data': None})

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        return JSONResponse(status_code=exc.status, content={'code': exc.code, 'message': exc.message, 'data': None})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        errors = '; '.join('.'.join(str(x) for x in error['loc'][1:]) + ': ' + error['msg'] for error in exc.errors())
        return JSONResponse(status_code=422, content={'code': 2001, 'message': errors, 'data': None})

    @app.exception_handler(IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(status_code=409, content={'code': 2001, 'message': '数据重复或存在引用关系，请刷新后重试', 'data': None})

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request, exc):
        logging.getLogger('kangyang').error('Database operation failed: %s', type(exc).__name__)
        return JSONResponse(status_code=503, content={'code': 5001, 'message': '数据库暂时不可用，请稍后重试', 'data': None})

    @app.exception_handler(Exception)
    async def unhandled_error(request, exc):
        logging.getLogger('kangyang').error('Request failed: %s', type(exc).__name__)
        return JSONResponse(status_code=500, content={'code': 5001, 'message': '服务器内部错误', 'data': None})
