from abc import ABC, abstractmethod
from .client import ConsentClient, AccountsClient, CardsClient, TransactionsClient


class AbstractOpenFinanceProvider(ABC):
    """Abstraction for Open Finance providers."""

    def __init__(self, name, base_url=None, token=None):
        self.name = name
        self.base_url = base_url
        self.token = token
        self.consent_client = ConsentClient(base_url, token=token) if base_url else None
        self.accounts_client = AccountsClient(base_url, token=token) if base_url else None
        self.cards_client = CardsClient(base_url, token=token) if base_url else None
        self.transactions_client = TransactionsClient(base_url, token=token) if base_url else None

    @abstractmethod
    def create_consent(self, bank_id, scopes=None, cpf_cnpj=None):
        raise NotImplementedError

    @abstractmethod
    def get_consent(self, consent_id):
        raise NotImplementedError

    @abstractmethod
    def revoke_consent(self, consent_id):
        raise NotImplementedError

    @abstractmethod
    def get_accounts(self, consent_id):
        raise NotImplementedError

    @abstractmethod
    def get_cards(self, consent_id):
        raise NotImplementedError

    @abstractmethod
    def get_transactions(self, consent_id, from_date=None, to_date=None):
        raise NotImplementedError

    def consent_payload(self, bank_id, scopes=None, cpf_cnpj=None):
        if scopes is None:
            scopes = [
                "CONSENT_ACCOUNT_OWN", "CONSENT_ACCOUNT_BALANCE", "CONSENT_ACCOUNT_TRANSACTIONS",
                "CONSENT_CARD_MECHATRANSACTIONS", "CONSENT_CARD_AUTHORIZATIONS",
            ]
        debtors = []
        if cpf_cnpj:
            debtors.append({"identification": cpf_cnpj})
        return {
            "data": {
                "permissions": scopes,
                "expirationDateTime": "2030-12-31T23:59:59Z",
                "transactionFromDateTime": "2024-01-01T00:00:00Z",
                "transactionToDateTime": "2026-12-31T23:59:59Z",
                "debtorAccount": {"identification": cpf_cnpj or bank_id},
            },
            "risk": {},
        }
