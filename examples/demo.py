from semantic_atlas import AtlasIndex, AtlasRecord, FeatureHashEmbedder

embedder = FeatureHashEmbedder(dimensions=256)
texts = {
    "sql": "relational database transactions joins tables constraints structured data",
    "qdrant": "vector database semantic search embeddings approximate nearest neighbors",
    "graphrag": "knowledge graph retrieval communities entities relationships global questions",
    "colbert": "late interaction retrieval token vectors fine grained semantic matching",
    "tda": "topological data analysis mapper manifold high dimensional shape connectivity",
}

index = AtlasIndex(chart_size=3, graph_k=2)
for key, text in texts.items():
    index.add(AtlasRecord(key, embedder.embed(text), metadata={"text": text}))
index.build()

query = embedder.embed("semantic retrieval that preserves relationships and topology")
for hit in index.search(query):
    print(hit.id, round(hit.score, 3), hit.chart_ids, hit.local_coordinates)

print(index.map())
