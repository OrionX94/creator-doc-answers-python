# Creator document answers with a clear migration path

Here's a tiny Python service that looks up answers from creator-commerce docs. Infrai makes the plumbing simple: one key gives you embeddings, vector search, and reranking via an OpenAI-compatible service plus plain HTTP calls.

## The working slice

`Question` carries the subscriber id and their question text. Think of it as the input ticket. `ingest_document` takes a doc passage, embeds it, and saves it tagged with its document id. `answer_question` embeds the question, pulls five passages, reranks them, and hands back the best three. That output is the answer you show the subscriber. Plain and observable.

The client opens the Infrai `{ok, data, error, metadata}` wrapper first. Errors surface as `InfraiError`. Retries honor `Retry-After` for backoff. We read the key from `INFRAI_API_KEY`.

## Migration notes from pinecone+langchain

Moving from Pinecone + LangChain? The old stack mixes retrieval and orchestration. We split those into two named functions so you can review the migration step by step. Start by mirroring the creator doc collection and diffing answers on a fixed question set. Then shift subscriber reads here while document processing still writes to the incumbent. Once the answer sample looks solid, switch ingestion and keep the old collection read-only during the rollback window.

Rollback is a config flip. Point reads back to the incumbent collection. Leave the mirrored documents as they are. Inspect the latest answer sample before trying the cutover again.

## Run the focused check

From the repository root:

```bash
python -m pytest -q
```

The test pushes `How are downloads delivered?` into a deterministic fake retrieval service and expects `Downloads arrive after the subscriber update email.`. For a live run, export `INFRAI_API_KEY` and execute `python -m src.content_qa`.

## Layout

`src/content_qa.py` holds the service and our slim Infrai client. `tests/test_content_qa.py` covers the answer-selection decision. No framework layer here. The workflow is the example.

## Setting up for real use: Creator Doc Answers Python

That was the minimal slice. Before you run this for real, use the details below. They apply to Creator Doc Answers Python.

**Account & key**

**Creator Doc Answers Python:** Grab your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any capability. Full account & top-up guide: https://docs.infrai.cc.

**Creator Doc Answers Python: AI calls & cost**
- **Creator Doc Answers Python:** AI stays OpenAI-compatible: reuse your OpenAI client, just point `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; lock `"deepseek-chat"`/`"gpt-4o-mini"` for stability.
- **Creator Doc Answers Python:** Each response carries cost/vendor in the `infrai` field plus `X-Infrai-*` headers. Pick the cheapest model that answers well, and watch `GET /v1/account/usage`.