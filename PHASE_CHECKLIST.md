# Project Phase Checklist

This document outlines the tasks and verification steps for Phases ZERO through THREE of the RAG system testing.

## Phase ZERO: Cleanup & Reset

**Objective:** Ensure a completely clean slate for testing. Remove all existing data from databases and file storage.

1.  **Stop Backend Service**
    -   Ensure `run_backend.bat` or the Python process is stopped.

2.  **Clear MSSQL Database (`LocalLLMChatDB`)**
    -   Connect to the local SQL Server instance using SSMS or a script.
    -   Execute the following SQL to clear application tables (order matters for foreign keys):
        ```sql
        USE LocalLLMChatDB;
        DELETE FROM MessageContext;
        DELETE FROM Attachments;
        DELETE FROM Messages;
        DELETE FROM ChatTags;
        DELETE FROM Tags;
        DELETE FROM Chats;
        -- Optional: DBCC CHECKIDENT ('TableName', RESEED, 0) to reset Identity columns if desired.
        ```
    -   *Verification:* Run `SELECT COUNT(*) FROM [TableName]` for each table to confirm they are 0.

3.  **Clear PostgreSQL Vector Database (`rag_vector_db`)**
    -   Connect to the Docker PostgreSQL instance (e.g., using pgAdmin or `psql`).
    -   Execute the following SQL:
        ```sql
        TRUNCATE TABLE document_chunks;
        ```
    -   *Verification:* `SELECT COUNT(*) FROM document_chunks;` should return 0.

4.  **Clear File Storage**
    -   Navigate to `backend/storage/uploads`.
    -   Delete all files in this directory.
    -   *Verification:* Directory should be empty.

---

## Phase ONE: Ingestion Testing

**Objective:** accurate document upload, text extraction, chunking, and embedding.

1.  **Start Services**
    -   Start Backend: `run_backend.bat`.
    -   Start Frontend (if testing via UI): `run_frontend.bat`.
    -   Ensure Ollama is running (`ollama serve`) and `momic-embed-text` model is pulled (`ollama pull nomic-embed-text`).

2.  **Test Upload & Ingestion**
    -   **Action:** Upload a sample PDF (e.g., a policy document or technical manual) via the UI or API (`POST /api/upload/`).
    -   **backend Log Check:** Watch for "Processing file...", "Document converted", "Generated X chunks", "Indexed X chunks to Vector DB".

3.  **Verification Steps**
    -   **File Storage:** Confirm the file exists in `backend/storage/uploads`.
    -   **MSSQL `Attachments` Table:**
        -   Check for a new row.
        -   Verify `file_path` is correct.
        -   Verify `extracted_text` column is populated (it should contain the Markdown text).
        -   Note the `id` of the attachment.
    -   **PostgreSQL `document_chunks` Table:**
        -   Run `SELECT COUNT(*) FROM document_chunks WHERE doc_id = 'YOUR_ATTACHMENT_ID'`.
        -   Confirm count equals the "Generated X chunks" from logs.
        -   Inspect a row: `SELECT * FROM document_chunks LIMIT 1;`. Verify `embedding` is not null and `text` contains readable content.

---

## Phase TWO: Summarization Testing

**Objective:** consistent and accurate document summaries.

1.  **Create Chat**
    -   **Action:** Start a new chat session via UI or API (`POST /api/chat/`).

2.  **Request Summary**
    -   **Action:** Send a message: "Please summarize the uploaded document."
    -   **Ensure Context:** Make sure the UI sends the specific `attachment_id` in the message payload or that the backend is configured to look up the chat's attachments.
    -   *Technically:* The backend `chats.py` logic retrieves chunks based on the query. For a general summary, we rely on semantic search finding the "introduction" or "summary" sections of the doc, OR we might need to implement a specific "read whole doc" if chunk retrieval isn't sufficient for a full summary. 
    -   *Note:* Standard RAG retrieves specific chunks. A "whole document summary" might require a different approach (e.g., recursive summarization) in future phases. For now, we test if it can summarize based on *retrieved* relevant chunks (e.g. Introduction/Conclusion).

3.  **Verification Steps**
    -   **Response:** Check if the Assistant provides a coherent summary.
    -   **Logs:** Verify `injest.retrieve_relevant_chunks` was called.
    -   **MSSQL `Messages` Table:**
        -   Check the last User message.
        -   Check `augmented_content` column. Does it contain `--- DOCUMENT: ... ---` blocks?
        -   If `augmented_content` is empty/null, RAG failed to retrieve context.

---

## Phase THREE: Document Chat (Q&A)

**Objective:** accurate answers to specific questions based *only* on the document.

1.  **Ask Specific Question**
    -   **Action:** Ask a question whose answer is buried in the middle of the document (not just the intro).
        -   *Example:* "What is the maximum penalty for violation X?" or "What is the configuration parameter for Y?"

2.  **Verification Steps**
    -   **Response:** The answer should be factually correct according to the document.
        -   It should NOT be a generic answer from the LLM's pre-training (hallucination).
        -   Ideally, it cites the document context implicitly.
    -   **Logs/Debug:**
        -   Check "Generated Search Query" (if web search is enabled, but strictly for Doc Chat, disable web search).
        -   Check retrieved chunks in logs. Do they contain the specific paragraph with the answer?
    -   **MSSQL `MessageContext` Table:**
        -   Query `SELECT * FROM MessageContext WHERE message_id = [Current_Message_ID]`.
        -   Verify that the `content` column contains the specific text snippet needed to answer the question.
        -   This proves the Vector Search successfully found the right "Needle in the haystack".

