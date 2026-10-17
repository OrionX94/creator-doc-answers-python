from src.content_qa import Question, answer_question


class FakeClient:
    def embedding(self, text):
        return [0.1, 0.2]

    def query(self, collection, embedding, top_k):
        return [{"metadata": {"text": "Downloads arrive after the subscriber update email."}}]

    def rerank(self, query, candidates, top_k):
        return [{"index": 0}]


def test_answer_uses_ranked_creator_document():
    result = answer_question(FakeClient(), Question("sub-7", "How are downloads delivered?"))
    assert result == "Downloads arrive after the subscriber update email."
