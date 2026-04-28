import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from jsonrpcserver import dispatch

# Import rpc_methods so all @method decorators are registered
import src.rpc_methods  # noqa: F401

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def transfer_rpc(request):
    """
    Single JSON-RPC endpoint for all transfer.* methods.
    POST /api/transfer/
    Content-Type: application/json
    """
    print("RPC METHODS LOADED") 
    try:
        body = request.body.decode("utf-8")
        logger.debug(f"RPC request: {body}")
        response = dispatch(body)
        logger.debug(f"RPC response: {response}")
        return JsonResponse(json.loads(response), safe=False)
    except Exception as exc:
        logger.exception(f"RPC dispatch error: {exc}")
        return JsonResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status=400,
        )
    
