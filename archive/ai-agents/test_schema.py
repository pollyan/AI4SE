from backend.agents.lisa.prompts.artifacts import format_schema_for_prompt, get_artifact_json_schemas
import json
schemas = get_artifact_json_schemas()
print(json.dumps(format_schema_for_prompt(schemas["requirement"]), indent=2, ensure_ascii=False))
