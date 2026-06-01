from .base import AbstractOpenFinanceProvider


class RealOpenFinanceProvider(AbstractOpenFinanceProvider):
    """Production provider for real Open Finance environments.
    
    Uses actual HTTP clients to make requests to the official Open Finance API.
    Requires base_url and token to be provided via environment variables or constructor.
    """

    def __init__(self, base_url=None, token=None):
        if not base_url:
            raise ValueError(
                "RealOpenFinanceProvider requires base_url. "
                "Set OPEN_FINANCE_BASE_URL environment variable or pass base_url to constructor."
            )
        if not token:
            raise ValueError(
                "RealOpenFinanceProvider requires token. "
                "Set OPEN_FINANCE_TOKEN environment variable or pass token to constructor."
            )
        super().__init__("real", base_url=base_url, token=token)

    def create_consent(self, bank_id, scopes=None, cpf_cnpj=None):
        """Create consent at the official Open Finance API.
        
        POST /open-banking/v1.0/consents
        """
        if not self.consent_client:
            raise RuntimeError("Consent client not initialized.")
        payload = self.consent_payload(bank_id, scopes=scopes, cpf_cnpj=cpf_cnpj)
        response = self.consent_client.create_consent(payload)
        return {
            "consent_id": response.get("data", {}).get("consentId"),
            "status": response.get("data", {}).get("status"),
            "deep_link": None,  # Real API does not provide deep link
        }

    def get_consent(self, consent_id):
        """Fetch consent details from the official Open Finance API.
        
        GET /open-banking/v1.0/consents/{consentId}
        """
        if not self.consent_client:
            raise RuntimeError("Consent client not initialized.")
        response = self.consent_client.get_consent(consent_id)
        return {
            "consent_id": response.get("data", {}).get("consentId"),
            "status": response.get("data", {}).get("status"),
            "created_at": response.get("data", {}).get("creationDateTime"),
        }

    def revoke_consent(self, consent_id):
        """Revoke consent at the official Open Finance API.
        
        DELETE /open-banking/v1.0/consents/{consentId}
        """
        if not self.consent_client:
            raise RuntimeError("Consent client not initialized.")
        response = self.consent_client.revoke_consent(consent_id)
        return {
            "consent_id": consent_id,
            "status": "REVOKED",
            "response": response,
        }

    def get_accounts(self, consent_id):
        """Fetch accounts from the official Open Finance API.
        
        GET /open-banking/v1.0/accounts?consentId={consentId}
        """
        if not self.accounts_client:
            raise RuntimeError("Accounts client not initialized.")
        response = self.accounts_client.get_accounts(consent_id)
        return {
            "consent_id": consent_id,
            "accounts": [
                {
                    "account_id": account.get("accountId"),
                    "bank": account.get("institution", {}).get("name"),
                    "type": account.get("type"),
                    "currency": account.get("currency"),
                    "balance": account.get("accountSubType", {}).get("balance"),
                }
                for account in response.get("data", [])
            ],
        }

    def get_cards(self, consent_id):
        """Fetch cards from the official Open Finance API.
        
        GET /open-banking/v1.0/cards?consentId={consentId}
        """
        if not self.cards_client:
            raise RuntimeError("Cards client not initialized.")
        response = self.cards_client.get_cards(consent_id)
        return {
            "consent_id": consent_id,
            "cards": [
                {
                    "card_id": card.get("cardId"),
                    "brand": card.get("brand"),
                    "last_digits": card.get("lastNumbers"),
                    "status": card.get("status"),
                    "limit": card.get("creditLimit", {}).get("amount"),
                    "available_limit": card.get("creditLimit", {}).get("availableAmount"),
                }
                for card in response.get("data", [])
            ],
        }

    def get_transactions(self, consent_id, from_date=None, to_date=None):
        """Fetch transactions from the official Open Finance API.
        
        GET /open-banking/v1.0/transactions?consentId={consentId}&from={from}&to={to}
        """
        if not self.transactions_client:
            raise RuntimeError("Transactions client not initialized.")
        response = self.transactions_client.get_transactions(consent_id, from_date=from_date, to_date=to_date)
        return {
            "consent_id": consent_id,
            "transactions": [
                {
                    "transaction_id": txn.get("transactionId"),
                    "account_id": txn.get("accountId"),
                    "amount": float(txn.get("amount", 0)),
                    "currency": txn.get("currency"),
                    "booking_date": txn.get("transactionDate"),
                    "description": txn.get("description"),
                    "type": txn.get("type"),
                }
                for txn in response.get("data", [])
            ],
        }
