# -*- coding: utf-8 -*-
"""
# RAG with LLaMa 13B

In this notebook we'll explore how we can use the open source **Llama-13b-chat** model in both Hugging Face transformers and LangChain.

---

🚨 _Note that running this on CPU is sloooow. If running on Google Colab you can avoid this by going to **Runtime > Change runtime type > Hardware accelerator > GPU > GPU type > T4**. This should be included within the free tier of Colab._

---

We start by doing a `pip install` of all required libraries.
"""

!pip install -qU \
  transformers==4.31.0 \
  sentence-transformers==2.2.2 \
  pinecone-client==2.2.2 \
  datasets==2.14.0 \
  accelerate==0.21.0 \
  einops==0.6.1 \
  langchain==0.0.240 \
  xformers==0.0.20 \
  bitsandbytes==0.41.0

"""## Initializing the Hugging Face Embedding Pipeline

We begin by initializing the embedding pipeline that will handle the transformation of our docs into vector embeddings. We will use the `sentence-transformers/all-MiniLM-L6-v2` model for embedding.
"""

from torch import cuda
from langchain.embeddings.huggingface import HuggingFaceEmbeddings

embed_model_id = 'sentence-transformers/all-MiniLM-L6-v2'

device = f'cuda:{cuda.current_device()}' if cuda.is_available() else 'cpu'

embed_model = HuggingFaceEmbeddings(
    model_name=embed_model_id,
    model_kwargs={'device': device},
    encode_kwargs={'device': device, 'batch_size': 32}
)

"""We can use the embedding model to create document embeddings like so:"""

docs = [
    "this is one document",
    "and another document"
]

embeddings = embed_model.embed_documents(docs)

print(f"We have {len(embeddings)} doc embeddings, each with "
      f"a dimensionality of {len(embeddings[0])}.")

"""## Building the Vector Index

We now need to use the embedding pipeline to build our embeddings and store them in a Pinecone vector index. To begin we'll initialize our index, for this we'll need a [free Pinecone API key](https://app.pinecone.io/).
"""

import os
import pinecone

# get API key from app.pinecone.io and environment from console
pinecone.init(
    api_key=os.environ.get('PINECONE_API_KEY') or 'pinecone_api_key',
    environment=os.environ.get('PINECONE_ENVIRONMENT') or 'gcp-starter'
)

"""Now we initialize the index."""

import time

index_name = 'llama-2-rag'

if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        index_name,
        dimension=len(embeddings[0]),
        metric='cosine'
    )
    # wait for index to finish initialization
    while not pinecone.describe_index(index_name).status['ready']:
        time.sleep(1)

"""Now we connect to the index:"""

index = pinecone.Index(index_name)
index.describe_index_stats()

"""With our index and embedding process ready we can move onto the indexing process itself. For that, we'll need a dataset. We will use a set of Arxiv papers related to (and including) the Llama 2 research paper."""

from datasets import load_dataset

data = load_dataset(
    'jamescalam/llama-2-arxiv-papers-chunked',
    split='train'
)
data

"""We will embed and index the documents like so:"""

data = data.to_pandas()

batch_size = 32

for i in range(0, len(data), batch_size):
    i_end = min(len(data), i+batch_size)
    batch = data.iloc[i:i_end]
    ids = [f"{x['doi']}-{x['chunk-id']}" for i, x in batch.iterrows()]
    texts = [x['chunk'] for i, x in batch.iterrows()]
    embeds = embed_model.embed_documents(texts)
    # get metadata to store in Pinecone
    metadata = [
        {'text': x['chunk'],
         'source': x['source'],
         'title': x['title']} for i, x in batch.iterrows()
    ]
    # add to Pinecone
    index.upsert(vectors=zip(ids, embeds, metadata))

index.describe_index_stats()

"""## Initializing the Hugging Face Pipeline

The first thing we need to do is initialize a `text-generation` pipeline with Hugging Face transformers. The Pipeline requires three things that we must initialize first, those are:

* A LLM, in this case it will be `meta-llama/Llama-2-13b-chat-hf`.

* The respective tokenizer for the model.

We'll explain these as we get to them, let's begin with our model.

We initialize the model and move it to our CUDA-enabled GPU. Using Colab this can take 5-10 minutes to download and initialize the model.
"""

from torch import cuda, bfloat16
import transformers

model_id = 'TheBloke/Llama-2-7b-Chat-GPTQ'

device = f'cuda:{cuda.current_device()}' if cuda.is_available() else 'cpu'

# set quantization configuration to load large model with less GPU memory
# this requires the `bitsandbytes` library
bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16
)

# begin initializing HF items, need auth token for these
hf_auth = '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'
model_config = transformers.AutoConfig.from_pretrained(
    model_id,
    use_auth_token=hf_auth
)

model = transformers.AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    config=model_config,
    quantization_config=bnb_config,
    device_map='auto',
    use_auth_token=hf_auth
)
model.eval()
print(f"Model loaded on {device}")

"""The pipeline requires a tokenizer which handles the translation of human readable plaintext to LLM readable token IDs. The Llama 2 13B models were trained using the Llama 2 13B tokenizer, which we initialize like so:"""

tokenizer = transformers.AutoTokenizer.from_pretrained(
    model_id,
    use_auth_token=hf_auth
)

"""Now we're ready to initialize the HF pipeline. There are a few additional parameters that we must define here. Comments explaining these have been included in the code."""

generate_text = transformers.pipeline(
    model=model, tokenizer=tokenizer,
    return_full_text=True,  # langchain expects the full text
    task='text-generation',
    # we pass model parameters here too
    temperature=0.0,  # 'randomness' of outputs, 0.0 is the min and 1.0 the max
    max_new_tokens=512,  # mex number of tokens to generate in the output
    repetition_penalty=1.1  # without this output begins repeating
)

"""Confirm this is working:"""

res = generate_text("Explain to me the difference between nuclear fission and fusion.")
print(res[0]["generated_text"])

"""Now to implement this in LangChain"""

from langchain.llms import HuggingFacePipeline

llm = HuggingFacePipeline(pipeline=generate_text)

llm(prompt="Explain to me the difference between nuclear fission and fusion.")

"""We still get the same output as we're not really doing anything differently here, but we have now added **Llama 2 13B Chat** to the LangChain library. Using this we can now begin using LangChain's advanced agent tooling, chains, etc, with **Llama 2**.

## Initializing a RetrievalQA Chain

For **R**etrieval **A**ugmented **G**eneration (RAG) in LangChain we need to initialize either a `RetrievalQA` or `RetrievalQAWithSourcesChain` object. For both of these we need an `llm` (which we have initialized) and a Pinecone index — but initialized within a LangChain vector store object.

Let's begin by initializing the LangChain vector store, we do it like so:
"""

from langchain.vectorstores import Pinecone

text_field = 'text'  # field in metadata that contains text content

vectorstore = Pinecone(
    index, embed_model.embed_query, text_field
)

"""We can confirm this works like so:"""

query = 'what makes llama 2 special?'

vectorstore.similarity_search(
    query,  # the search query
    k=3  # returns top 3 most relevant chunks of text
)

"""Looks good! Now we can put our `vectorstore` and `llm` together to create our RAG pipeline."""

from langchain.chains import RetrievalQA

rag_pipeline = RetrievalQA.from_chain_type(
    llm=llm, chain_type='stuff',
    retriever=vectorstore.as_retriever()
)

rag_pipeline('what is so special about llama 2?')

rag_pipeline('what safety measures were used in the development of llama 2?')

rag_pipeline('what red teaming procedures were followed for llama 2?')

rag_pipeline('how does the performance of llama 2 compare to other local LLMs?')

