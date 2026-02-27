from langchain_core.utils.function_calling import convert_to_openai_function
from backend.agents.lisa.schemas import UpdateStructuredArtifact

schema = convert_to_openai_function(UpdateStructuredArtifact)
print("Tool name:", schema.get('name'))
