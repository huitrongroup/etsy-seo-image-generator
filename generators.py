import os
import anthropic
from models import ContentRequest, ContentResult
from prompts import build_generation_prompt, build_improve_prompt
from validators import validate_content

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def generate_content(req: ContentRequest) -> ContentResult:
    client = _get_client()
    prompt = build_generation_prompt(req)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_content = message.content[0].text.strip()
    result = ContentResult(request=req, content=raw_content, score=0.0)
    return validate_content(result)


def improve_content(result: ContentResult) -> ContentResult:
    if not result.issues:
        return result

    client = _get_client()
    prompt = build_improve_prompt(result.content, result.issues, result.request.season.value)

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    improved = message.content[0].text.strip()
    new_result = ContentResult(request=result.request, content=improved, score=0.0)
    return validate_content(new_result)


def generate_variants(req: ContentRequest, n: int = 3) -> list[ContentResult]:
    return [generate_content(req) for _ in range(n)]
