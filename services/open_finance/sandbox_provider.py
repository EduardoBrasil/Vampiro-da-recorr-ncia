from .base import AbstractOpenFinanceProvider
from .mock_provider import MockOpenFinanceProvider


class SandboxOpenFinanceProvider(AbstractOpenFinanceProvider):
    """Sandbox provider that mirrors official Open Finance swagger clients."""

    def __init__(self, base_url=None, token=None):
        super().__init__("sandbox", base_url=base_url, token=token)
        self.mock = MockOpenFinanceProvider(base_url=base_url, token=token)

    def create_consent(self, bank_id, scopes=None, cpf_cnpj=None):
        if self.base_url:
            payload = self.consent_payload(bank_id, scopes=scopes, cpf_cnpj=cpf_cnpj)
            return self.consent_client.create_consent(payload)
        return self.mock.create_consent(bank_id, scopes=scopes, cpf_cnpj=cpf_cnpj)

    def get_consent(self, consent_id):
        if self.base_url:
            return self.consent_client.get_consent(consent_id)
        return self.mock.get_consent(consent_id)

    def revoke_consent(self, consent_id):
        if self.base_url:
            return self.consent_client.revoke_consent(consent_id)
        return self.mock.revoke_consent(consent_id)

    def get_accounts(self, consent_id):
        if self.base_url:
            return self.accounts_client.get_accounts(consent_id)
        return self.mock.get_accounts(consent_id)

    def get_cards(self, consent_id):
        if self.base_url:
            return self.cards_client.get_cards(consent_id)
        return self.mock.get_cards(consent_id)

    def get_transactions(self, consent_id, from_date=None, to_date=None):
        if self.base_url:
            return self.transactions_client.get_transactions(consent_id, from_date=from_date, to_date=to_date)
        return self.mock.get_transactions(consent_id, from_date=from_date, to_date=to_date)
