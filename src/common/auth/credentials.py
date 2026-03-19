from functools import lru_cache

from azure.identity import DefaultAzureCredential


@lru_cache(maxsize=1)
def get_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()


def get_access_token(scope: str = "https://cognitiveservices.azure.com/.default") -> str:
    return get_credential().get_token(scope).token
