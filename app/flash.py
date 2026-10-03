"""Mensajes flash de un solo uso en sesión — equivalente a django.contrib.messages."""


def flash(request, text: str, tag: str = "info") -> None:
    messages = request.session.get("messages") or []
    messages.append({"tags": tag, "text": text})
    request.session["messages"] = messages


def pop_messages(request) -> list[dict]:
    messages = request.session.pop("messages", [])
    return messages
