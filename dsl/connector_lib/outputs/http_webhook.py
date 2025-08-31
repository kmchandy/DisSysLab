from __future__ import annotations
from typing import Any, Dict, List
import json
from urllib import request, error
from .base import OutputConnector


class OutputConnectorHTTPWebhook(OutputConnector):
    """
    POST payload as JSON to a webhook URL.

    Message to 'in':
      {"cmd":"flush","payload":[...], "meta":{"url":"https://...","headers":{"Authorization":"Bearer ..."}}}

    Behavior:
      - Sends JSON body: {"items":[ ... ]} (list is preserved)
      - Raises on HTTP errors
    """

    def _flush(self, payload: List[Any], meta: Dict[str, Any]) -> None:
        url = meta["url"]
        headers = {"Content-Type": "application/json"}
        headers.update(meta.get("headers", {}))
        body = json.dumps({"items": payload}).encode("utf-8")

        req = request.Request(url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                # 2xx only; any other code triggers an HTTPError
                if not (200 <= resp.status < 300):
                    raise error.HTTPError(
                        url, resp.status, "Non-2xx", resp.headers, None)
        except error.HTTPError as e:
            # Surface a useful error message
            raise RuntimeError(
                f"Webhook POST failed: {e.code} {e.reason}") from e
        except Exception as e:
            raise RuntimeError(f"Webhook POST failed: {e}") from e
