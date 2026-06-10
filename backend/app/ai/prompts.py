from string import Template

DEFAULT_SYSTEM_INSTRUCTION = (
    "You are a concise assistant for an email productivity app. "
    "Keep answers short and practical."
)

STRUCTURED_JSON_SYSTEM = (
    "Respond with valid JSON only. Do not use markdown fences or extra text."
)


def build_prompt(template: str, **variables: str) -> str:
    """Render a prompt template with safe substitution."""
    return Template(template).safe_substitute(**variables)


def build_system_instruction(instruction: str | None = None) -> str:
    if not instruction or not instruction.strip():
        return DEFAULT_SYSTEM_INSTRUCTION
    return instruction.strip()


def inject_context(*, context: str, task: str) -> str:
    """Combine context and task into a compact prompt for small models."""
    context = context.strip()
    task = task.strip()
    if not context:
        return task
    return f"Context:\n{context}\n\nTask:\n{task}"


def structured_output_prompt(*, task: str, schema_hint: str) -> str:
    """Build a short prompt that asks for JSON matching a schema hint."""
    return inject_context(
        context=f"Output schema:\n{schema_hint}",
        task=task,
    )
