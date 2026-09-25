"""Shared service-definition normalization helpers."""


def normalize_service_definition(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())
