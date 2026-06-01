import json
import urllib.request
import urllib.error


class OpenFinanceClient:
    """Base HTTP client for Open Finance Swagger-style APIs."""

    def __init__(self, base_url, token=None, timeout=10):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token
        self.timeout = timeout

    def _build_url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def _build_headers(self, extra=None):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def request(self, method, path, data=None, headers=None):
        url = self._build_url(path)
        body = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        request_headers = self._build_headers(headers)
        request = urllib.request.Request(url, data=body, headers=request_headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode("utf-8")
                return json.loads(content or "{}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenFinance API error: {exc.code} {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenFinance transport error: {exc}") from exc


class ConsentClient(OpenFinanceClient):
    """Client for official consent endpoints."""

    def create_consent(self, payload):
        return self.request("POST", "/open-banking/v1.0/consents", data=payload)

    def get_consent(self, consent_id):
        return self.request("GET", f"/open-banking/v1.0/consents/{consent_id}")

    def revoke_consent(self, consent_id):
        return self.request("DELETE", f"/open-banking/v1.0/consents/{consent_id}")


class AccountsClient(OpenFinanceClient):
    """Client for official accounts endpoints."""

    def get_accounts(self, consent_id):
        return self.request("GET", f"/open-banking/v1.0/accounts?consent_id={consent_id}")


class CardsClient(OpenFinanceClient):
    """Client for official cards endpoints."""

    def get_cards(self, consent_id):
        return self.request("GET", f"/open-banking/v1.0/cards?consent_id={consent_id}")


class TransactionsClient(OpenFinanceClient):
    """Client for official transactions endpoints."""

    def get_transactions(self, consent_id, from_date=None, to_date=None):
        query = [f"consent_id={consent_id}"]
        if from_date:
            query.append(f"from={from_date}")
        if to_date:
            query.append(f"to={to_date}")
        return self.request("GET", f"/open-banking/v1.0/transactions?{'&'.join(query)}")
