### **RAG**



|Phase-1|ingest documents;pdfs,mds,webpages->chunk them to pieces;500-800 tokens;100 tokens overlap between chunks->store chunks in a vector store->build a retrieval pipeline that pulls the top K most relevant chunks for a given query and generates the answer that cites where the information came from|orchestration: LangChain, LangGraph<br />Vector Store: ChromaDB, weaviate|
|-|-|-|
|Phase-2|implement a hybrid retrieval;combining traditional BM25 keyword search with vector based symantic search->add a cross-encoder re-ranker that takes the initial set of retrieved chunks and re-scores them using a model that evaluates the query and each chunk together as a pair->implement citation enforcement(system should explicitly decline to answer if retieved chunks do not support a specific response). store prompts in a version config files.|reranking: cohere, SBERT|
|Phase-3|curate a golden evaluation dataset of around 50-200 Q\&A pair that is manually verified for correctness-> write an offline evaluation script that measures faithfulness which essentially asks if the claims in the generated answer are actually supported by the retirieved chunks->wire this into CI pipeline so that every pull request automatically triggers an evaluation run, if quality drops below you threshold then the build fails.|Evaluation Framework: ragas|



