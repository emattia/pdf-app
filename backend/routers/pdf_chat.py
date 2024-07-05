from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import re
import os
import json
import subprocess
import requests


try:
    import pymupdf as fitz  # available with v1.24.3
except ImportError:
    import fitz

import numpy as np
from openai import OpenAI
import tensorflow_hub as hub
from fitz import Document as FitzDocument
from fastapi import APIRouter, UploadFile
from sklearn.neighbors import NearestNeighbors


router = APIRouter()

### Global variables. 😬 ###
pdf = None
# Routes provided in pdf_chat.py assume a single PDF in memory.
# TODO: Fix this if we want to support multiple PDFs or multiple users.
text_ls = None  # List of text from the PDF.
chunks = None  # List of vectors/embeddings.

### Keys
assert "OPENAI_API_KEY" in os.environ, "Please set OPENAI_API_KEY environment variable."
oai_compatible_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    # base_url="http://127.0.0.1:8000/v1", api_key="na"
)

### Tuning and model selection. ###
DEFAULT_WORD_LENGTH = 100
DEFAULT_BATCH_SIZE = 1000
DEFAULT_N_NEIGHBORS = 8
TEXT_EMBEDDING_MODEL_INFO = {
    'remote_path': 'https://tfhub.dev/google/universal-sentence-encoder/4',
    # "remote_path": "https://kaggle.com/models/google/universal-sentence-encoder/frameworks/TensorFlow2/variations/universal-sentence-encoder/versions/1",
    "local_path": "/tmp/models/universal-sentence-encoder",
    "model_name": "universal-sentence-encoder",
    "model_version": "4",
    "model_framework": "tensorflow",
    "pretrained_model_provider": "TensorFlow Hub",
    "use_case": "text-semantic-search",
}
LLM_MODEL_INFO = {
    "remote_path": "openAI",
    "local_path": None,
    "model_name": "gpt-4o",
    "model_version": None,
    "model_framework": "openai",
    "pretrained_model_provider": "OpenAI",
    "use_case": "document-chat",
}

# A big model container M_search.
# M_search affects what the user is shown
# by modeling similarity between chunks of text in 1 to N PDFs.
# M_search uses sklearn.neighbors.NearestNeighbors on Universal Sentence Encoder embeddings.
class SemanticSearchModel:
    """
    Manager for a semantic search model.

    args:
        None

    methods:
        fit(data: List[str], batch: int, n_neighbors: int) -> None:
            Fits the model M with the data.
        _get_text_embedding(texts: List[str], batch: int) -> np.ndarray:
            Returns the embeddings of the text.
    """

    def __init__(self):
        """
        `use` expects a path to unzipped Universal Sentence Encoder model from TensorFlow Hub.
        TODO: Support other models. sentence-transformers next.
        Use M_search = SemanticSearchModel() to create a new instance.
        M_search.fit(data) to fit the model when a PDF is uploaded.
        M_search(text) to get the nearest neighbors of a new text at inference time,
            to give the LLM a boost.
        """
        self._tfhub_download(
            TEXT_EMBEDDING_MODEL_INFO["remote_path"], 
            TEXT_EMBEDDING_MODEL_INFO["local_path"]
        )
        self.embedding_model = hub.load(TEXT_EMBEDDING_MODEL_INFO["local_path"])
        self.fitted = False

    def create_directory(self, path):
        """
        Create a directory if it does not exist.
        
        :param path: The directory path to create.
        """
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"[DEBUG] Created directory at {path}.")
        else:
            print(f"[DEBUG] Directory already exists at {path}.")

    def download_file(self, url, local_path):
        """
        Download a file from a URL to a local path.
        
        :param url: The URL to download the file from.
        :param local_path: The local path to save the downloaded file.
        """
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[DEBUG] Downloaded file from {url} to {local_path}")
        else:
            print(f"[ERROR] Failed to download file from {url}")
            response.raise_for_status()

    def extract_tar_file(self, tar_path, extract_to):
        """
        Extract a tar.gz file to a specified directory.
        
        :param tar_path: The path to the tar.gz file.
        :param extract_to: The directory to extract the contents to.
        """
        extract_process = subprocess.run(
            ["tar", "-zxvf", tar_path, "-C", extract_to],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if extract_process.returncode == 0:
            print(f"[DEBUG] Extracted tar file {tar_path} to {extract_to}")
        else:
            print(f"[ERROR] Failed to extract tar file: {extract_process.stderr.decode('utf-8')}")
            extract_process.check_returncode()

    def _tfhub_download(self, remote_url, local_dir):
        """
        Download and extract the TensorFlow Hub model to the local directory if it does not already exist.
        
        :param remote_url: The URL of the remote TensorFlow Hub model.
        :param local_dir: The local directory where the model should be saved.
        """
        if os.path.exists(local_dir):
            print("[DEBUG] Local directory exists.")
            return

        print("[DEBUG] Downloading TensorFlow Hub model.")
        self.create_directory(local_dir)
        
        tar_file_path = os.path.join(local_dir, "model.tar.gz")
        self.download_file(f"{remote_url}?tf-hub-format=compressed", tar_file_path)
        self.extract_tar_file(tar_file_path, local_dir)
        
        # Clean up the tar file
        os.remove(tar_file_path)
        print("[DEBUG] Download and extraction complete.")

    def _get_text_embedding(self, texts, batch_size=DEFAULT_BATCH_SIZE):
        """
        Gather a stack of embedded texts, packed batch_size at a time.
        """
        embeddings = []
        n_texts = len(texts)
        for batch_start_idx in range(0, n_texts, batch_size):
            text_batch = texts[batch_start_idx : (batch_start_idx + batch_size)]
            embedding_batch = self.embedding_model(text_batch)
            embeddings.append(embedding_batch)
        print("[DEBUG] Embedding batches:", len(embeddings))
        embeddings = np.vstack(embeddings)
        print("[DEBUG] Embedding reshaped:", embeddings.shape)
        return embeddings

    def fit(self, data, batch_size=DEFAULT_BATCH_SIZE, n_neighbors=DEFAULT_N_NEIGHBORS):
        """
        The only public method in this class.
        Fits the model with the data when a new PDF is uploaded.
        """
        self.data = data
        self.embeddings = self._get_text_embedding(data, batch_size=batch_size)
        n_neighbors = min(n_neighbors, len(self.embeddings))
        print(
            "[DEBUG] Fitting Nearest Neighbors model with %s neighbors." % n_neighbors
        )
        self.nn = NearestNeighbors(n_neighbors=n_neighbors)
        self.nn.fit(self.embeddings)
        print("[DEBUG] Fit complete.")
        self.fitted = True

    def __call__(self, text, return_data=True):
        """
        Inference time method.
        Return the nearest neighbors of a new text.
        """
        print("[DEBUG] Getting nearest neighbors of text:", text)
        embedding = self.embedding_model([text])
        print("[DEBUG] Embedding:", embedding.shape)
        neighbors = self.nn.kneighbors(embedding, return_distance=False)[0]
        if return_data:
            return [self.data[text_neighbs] for text_neighbs in neighbors]
        else:
            return neighbors

M_search = SemanticSearchModel()
# M_search is used in routes as a Python global variable. 😬


@router.post("/upload-pdf-url")
async def upload_pdf_from_url(url: str):
    raise NotImplementedError("This feature is not implemented yet.")


@router.post("/upload-pdf-file")
async def upload_pdf_from_file(uf: UploadFile):
    """
    UploadFile request makes a spooled file.
    It does a kind of buffering, storing the file in memory to a size, then store it on disk.
    Read more: https://fastapi.tiangolo.com/tutorial/request-files/#file-parameters-with-uploadfile
    """

    print("[INFO] Received: ", uf.filename)
    # NOTE: dumb logging now. good time to tee stuff or use actual logger
    if uf.content_type != "application/pdf":
        return {"Error": "Only PDF files are allowed!"}

    # TODO: Do we need to write the pdf to disk?
    # TODO: Keep an index of uploaded files and their paths that persists across users / sessions.
    pdf_bytes = uf.file.read()
    pdf_file_path = f"data/{uf.filename}"
    print("[INFO] Writing to disk: ", pdf_file_path)
    if not os.path.exists("data"):
        os.makedirs("data")
    with open(pdf_file_path, "wb") as f:
        f.write(pdf_bytes)
    print("[INFO] Processing PDF: ", pdf_file_path)
    process_pdf(pdf_file_path)
    # Have now created the RAG+LLM inputs, including setting M_search.
    global M_search
    if M_search is None:
        return {
            "message": "ERROR. PDF upload isn't working because M_search hasn't been set."
        }
    print("[INFO] Organizing prompt...")
    prompt = ""
    prompt += "search results:\n\n"
    # TODO: Add a check for the prompt length, depending on model.
    question = "What are the key points of the document?"
    topn_chunks = M_search(question)  # RAG🌶️
    for similar_chunk in topn_chunks:
        prompt += similar_chunk + "\n\n"
    message_history = [
        {
            "role": "system",
            "content": "You are an insightful and wise assistant. You discuss topics related to the search results, and no others."
            "Instructions: Provide an executive summary of the documents. "
            "Weave responses and citations into a coherent and succinct paragraph in the answer key of the output JSON. "
            "Answer step-by-step."
            "Return a JSON object with the following format: \n\n"
            "\n\n{\n"
            f'  "query": "{question}",\n'
            '   "summary": "...",\n',
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
    # print("[INFO] Sending request to OpenAI.", message_history)
    completion = oai_compatible_client.chat.completions.create(
        model=LLM_MODEL_INFO["model_name"],
        messages=message_history,
        response_format={"type": "json_object"},
    )
    out_json = completion.choices[0].message.content
    # TODO: Postprocessing.
    # print("[INFO] Done summarizing. Sending response.")
    return json.loads(out_json)


@router.get("/pdf-chat")
async def pdf_chat(question: str, ctx_messages: str):

    global M_search
    if M_search is None:
        return {"message": "ERROR. Upload a PDF file before chatting."}

    ctx_messages = json.loads(ctx_messages)
    prompt = ""
    prompt += "search results:\n\n"
    topn_chunks = M_search(question)
    for c in topn_chunks:
        prompt += c + "\n\n"
    message_history = [
        {
            "role": "system",
            "content": "You are an insightful and wise assistant that helps contextualize PDF documents. "
            "You discuss topics related to the search results, and no others, and you help your counterpart find what they are looking for quickly."
            "Instructions: Only reply to the query based on the search results given. "
            "Respond succinctly and precisely. Be informative but add minimal fluff."
            "Anchor responses based on the search results."
            "Cite each reference using [ Page N ] notation."
            "(every result has this number at the beginning). "
            "Weave responses and citations into a coherent and succinct paragraph in the answer key of the output JSON. "
            "Citation should also be done in a separate JSON field. "
            "Only include information found in the results and "
            "only answer what is asked. "
            "Return a JSON object with the following format: \n\n"
            "{\n"
            f'  "query": "{question}",\n'
            f'  "citations": "[{'Page Number'}]",\n'
            '  "answer": "Answer here"\n'
            "}\n\n"
            "Answer step-by-step. Include the page number in the most relevant citations. "
            "\n\n{\n"
            f'  "query": "{question}",\n'
            '   "citations": "...",\n'
            '   "answer": "...",\n',
        },
        *ctx_messages,
        {
            "role": "user",
            "content": prompt,
        },
    ]

    # TODO: Add a check for the prompt length, depending on model.
    # TODO: Content moderation. Flag PII.

    completion = oai_compatible_client.chat.completions.create(
        model=LLM_MODEL_INFO["model_name"],
        messages=message_history,
        response_format={"type": "json_object"},
    )
    out_json = completion.choices[0].message.content

    # TODO: Log request/response/and stuff in a to-be-eval'd DB.

    return json.loads(out_json)


def process_pdf(pdf_file_path):
    """
    This function processes the PDF file and prepares the data for the LLM.
    It is called pretty soon after the user uploads a PDF file.

    Extract text from the PDF file.
    Split the text into chunks.
    **Side effect**: store chunks. Fit new M_search. Set text_ls and chunks too based on new PDF.
    Make a new SemanticSearchModel model, put it in M_search and fit it with the chunks.
    """
    global M_search, text_ls, chunks
    # User is waiting since request gets to API server.
    text_ls = pdf_to_text(pdf_file_path)
    chunks = text_to_chunks(text_ls)
    M_search.fit([c[0] for c in chunks])
    # On return, loading screen stops for user.
    return chunks


################################################################
# Following is based on this repo:
# https://github.com/bhaskatripathi/pdfGPT/blob/main/api.py#L105
################################################################


def preprocess(text):
    """
    Apply rules to process one string of text that is extracted from a PDF.
    """
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def pdf_to_text(path, start_page=1, end_page=None):
    """
    Extracts text from a PDF file and preprocesses it.
    """
    doc = fitz.open(path)
    total_pages = doc.page_count
    if end_page is None:
        end_page = total_pages
    text_list = []
    for i in range(start_page - 1, end_page):
        text = doc.load_page(i).get_text("text")
        text = preprocess(text)
        text_list.append({"content": text, "page": i + 1})
    doc.close()
    return text_list


def text_to_chunks(
    texts,  # list of Dict[Tuple] like {'content'='', 'page': int})
    word_length=DEFAULT_WORD_LENGTH,
    start_page=1,
):
    text_toks = [(t["content"].split(" "), t["page"]) for t in texts]
    text_toks_len = len(text_toks)
    chunks = []
    for token_idx, words_and_page in enumerate(text_toks):
        words = words_and_page[0]
        n_words = len(words)
        page = words_and_page[1]
        for i in range(0, n_words, word_length):
            chunk = words[i : i + word_length]
            chunk_sz = len(chunk)
            if (
                (i + word_length) > n_words
                and (chunk_sz < word_length)
                and (text_toks_len != (token_idx + 1))
            ):
                text_toks[token_idx + 1] = (
                    chunk + text_toks[token_idx + 1][0],
                    text_toks[token_idx + 1][1],
                )
                continue
            chunk_join = " ".join(chunk).strip()
            # TODO: Improve way to add page number citation.
            # Rely less on LLM to do citation through token generation, maybe 🤨.
            chunk = f"[Page no. {token_idx+start_page}]" + " " + '"' + chunk_join + '"'
            chunks.append((chunk, page))
    return chunks
