import uuid
from .base import AbstractOpenFinanceProvider


class MockOpenFinanceProvider(AbstractOpenFinanceProvider):
    """Mock provider for local Open Finance validation."""

    def __init__(self, base_url=None, token=None):
        super().__init__("mock", base_url=base_url, token=token)

    def create_consent(self, bank_id, scopes=None, cpf_cnpj=None):
        consent_id = f"urn:bancocentral:consent:{uuid.uuid4()}"
        return {
            "consent_id": consent_id,
            "bank_id": bank_id,
            "status": "AUTHORIZED",
            "deep_link": f"/mock-bank/{bank_id}?consentId={consent_id}&cpf={cpf_cnpj or 'mock'}",
            "scopes": scopes or self.consent_payload(bank_id, cpf_cnpj=cpf_cnpj)["data"]["permissions"],
        }

    def get_consent(self, consent_id):
        return {
            "consent_id": consent_id,
            "status": "AUTHORIZED",
            "created_at": "2026-01-01T12:00:00Z",
        }

    def revoke_consent(self, consent_id):
        return {"consent_id": consent_id, "status": "REVOKED"}

    def get_accounts(self, consent_id):
        return {
            "consent_id": consent_id,
            "accounts": [
                {"account_id": "1234567890", "bank": "mock-bank", "type": "CHECKING", "currency": "BRL", "balance": 2543.20},
                {"account_id": "0987654321", "bank": "mock-bank", "type": "SAVINGS", "currency": "BRL", "balance": 10234.75},
            ],
        }

    def get_cards(self, consent_id):
        return {
            "consent_id": consent_id,
            "cards": [
                {"card_id": "card_001", "brand": "VISA", "last_digits": "1234", "status": "ACTIVE", "limit": 8000.0, "available_limit": 4620.0},
            ],
        }

    def get_transactions(self, consent_id, from_date=None, to_date=None):
        return {
            "consent_id": consent_id,
            "transactions": [
                {"transaction_id": "txn_001", "account_id": "1234567890", "amount": -89.9, "currency": "BRL", "booking_date": "2026-05-01", "description": "Netflix"},
                {"transaction_id": "txn_002", "account_id": "1234567890", "amount": -34.9, "currency": "BRL", "booking_date": "2026-05-09", "description": "Spotify"},
                {"transaction_id": "txn_003", "account_id": "0987654321", "amount": 1200.0, "currency": "BRL", "booking_date": "2026-05-15", "description": "Salary"},
            ],
        }
