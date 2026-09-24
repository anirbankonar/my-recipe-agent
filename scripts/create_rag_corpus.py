import os
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-03-d2603dc6aba2"
LOCATION = "us-central1"  # serverless mode is us-central1
GCS_PATH = "gs://smart-recipe-assistant-qwiklabs-gcp-03-d2603dc6aba2/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, medicinal herbs, dietary recommendations, and recipes described in this text. "
    "Ignore and omit all metadata, boilerplate, and license headers. "
    "Output clean, self-contained prose."
)

vertexai.init(project=PROJECT_ID, location=LOCATION)

# 1. Switch the region's RAG managed DB to serverless mode
cfg = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
try:
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )
    print("Updated RAG engine config to serverless mode.")
except Exception as e:
    print("Rag engine config update note:", e)

# 2. Create the corpus
corpus = rag.create_corpus(
    display_name="culpeper-herbal-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
print("CREATED_CORPUS_NAME:", corpus.name)

# 3. Import + parse + chunk + embed
resp = rag.import_files(
    corpus_name=corpus.name,
    paths=[GCS_PATH],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
    ),
    llm_parser=rag.LlmParserConfig(
        model_name="gemini-2.5-flash",
        custom_parsing_prompt=PARSING_PROMPT,
    ),
)
print("IMPORTED_FILES_COUNT:", resp.imported_rag_files_count)
