
# Llama-2-13B-RetrievalQA
---

This repository contains a Python script (`llama_2_13b_retrievalqa.py`) showcasing the integration of the Llama-13B-Chat model into a Retrieval Augmented Generation (RAG) setting using Hugging Face transformers and LangChain.

## Overview

The script demonstrates the following key functionalities:

1. **Environment Setup and Library Installation:** Installs required libraries for the project using pip.

2. **Initializing the Hugging Face Embedding Pipeline:** Initializes an embedding pipeline using the sentence-transformers/all-MiniLM-L6-v2 model for document embeddings.

3. **Building the Vector Index:** Sets up a Pinecone vector index to store document embeddings. Utilizes a dataset related to Llama 2 research papers for embedding and indexing.

4. **Initializing the Hugging Face Pipeline:** Loads a pre-trained Llama-2-7B-Chat-GPTQ model and its tokenizer for text generation using Hugging Face transformers.

5. **LangChain Integration:** Integrates the Hugging Face pipeline into LangChain, showcasing basic usage.

6. **Initializing a RetrievalQA Chain:** Sets up a RetrievalQA chain in LangChain, combining the Hugging Face pipeline and a Pinecone vector store for retrieval. Demonstrates the retrieval of relevant information.

## Prerequisites

- Python 3.6 or higher
- GPU (for optimal performance)
- Pinecone API Key (for building the vector index)
- Hugging Face Authentication Token (for model loading)

## Getting Started

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up Pinecone API Key and Hugging Face Authentication Token in the environment.

3. Run the script:

```bash
python llama_2_13b_retrievalqa.py
```

## Results

The script showcases the integration of Llama-13B-Chat into a RetrievalQA setting, allowing users to generate responses based on queries and retrieve relevant information.

## Acknowledgments

- The script uses models and libraries from Hugging Face and LangChain.


## License

This project is licensed under the [MIT License](LICENSE).

---
