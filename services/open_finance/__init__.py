from .mock_provider import MockOpenFinanceProvider
from .sandbox_provider import SandboxOpenFinanceProvider
from .real_provider import RealOpenFinanceProvider

PROVIDER_REGISTRY = {
    "mock": MockOpenFinanceProvider,
    "sandbox": SandboxOpenFinanceProvider,
    "real": RealOpenFinanceProvider,
}


def create_open_finance_provider(mode="mock", base_url=None, token=None):
    provider_class = PROVIDER_REGISTRY.get((mode or "").lower(), MockOpenFinanceProvider)
    return provider_class(base_url=base_url, token=token)


__all__ = [
    "MockOpenFinanceProvider",
    "SandboxOpenFinanceProvider",
    "RealOpenFinanceProvider",
    "create_open_finance_provider",
]
