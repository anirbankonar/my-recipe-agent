from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.parser.parser import parse_response, has_a2ui_parts


def get_a2ui_schema_manager(version: str = "0.8") -> A2uiSchemaManager:
    """Creates an A2uiSchemaManager instance configured with the Basic Catalog."""
    catalog_config = BasicCatalog().get_config(version)
    return A2uiSchemaManager(version=version, catalogs=[catalog_config])


def build_a2ui_prompt(role_description: str, version: str = "0.8") -> str:
    """Builds the complete system prompt using A2uiSchemaManager and Basic Catalog."""
    manager = get_a2ui_schema_manager(version)
    return manager.generate_system_prompt(
        role_description=role_description,
        include_schema=True,
        include_examples=True,
    )



async def a2ui_after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Callback triggered after model generation to parse and handle A2UI JSON output."""
    if not llm_response or not llm_response.content or not llm_response.content.parts:
        return llm_response

    text_parts = []
    for part in llm_response.content.parts:
        if getattr(part, "text", None):
            text_parts.append(part.text)

    full_text = "\n".join(text_parts)
    if full_text and has_a2ui_parts(full_text):
        parsed_parts = parse_response(full_text)
        a2ui_payloads = []
        for p in parsed_parts:
            if getattr(p, "a2ui_json", None):
                a2ui_payloads.extend(p.a2ui_json)

        if a2ui_payloads:
            if getattr(llm_response, "custom_metadata", None) is None:
                llm_response.custom_metadata = {}
            if isinstance(llm_response.custom_metadata, dict):
                llm_response.custom_metadata["a2ui"] = a2ui_payloads

    return llm_response
