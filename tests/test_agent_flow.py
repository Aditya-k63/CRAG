"""End-to-end graph flow tests with mocked retrieval + Groq.

These verify the LangGraph CRAG routing (retrieve -> evaluate ->
generate | web_fallback -> generate) behaves correctly for different question
types without needing a live database or API keys.
"""
import pytest

import rag_query


class FakeGroq:
    """Pretends to be a Groq client.

    The evaluation call (max_tokens=5) answers "yes"/"no" by scanning the
    user message for 'relevant'; generation calls return a canned answer.
    """

    def __init__(self):
        self.calls: list[str] = []
        self.chat = self._Chat(self)

    class _Message:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, content: str):
            self.message = FakeGroq._Message(content)

    class _Completion:
        def __init__(self, content: str):
            self.choices = [FakeGroq._Choice(content)]

    class _Completions:
        def __init__(self, owner: "FakeGroq"):
            self._owner = owner

        def create(self, messages, **kwargs):
            user = messages[-1]["content"]
            self._owner.calls.append(user)
            if "Answer exactly 'yes' or 'no':" in user:
                text = "yes" if "relevant" in user.lower() else "no"
            else:
                text = "Generated answer."
            return FakeGroq._Completion(text)

    class _Chat:
        def __init__(self, owner: "FakeGroq"):
            self.completions = FakeGroq._Completions(owner)


def fake_retrieve(query: str, top_k: int = 3):
    if "relevant" in query.lower():
        return [("relevant context about " + query, 0.95) for _ in range(top_k)]
    return [("unrelated gardening text", 0.05)]


@pytest.fixture
def patched_agent(monkeypatch):
    fake = FakeGroq()
    monkeypatch.setattr(rag_query, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(rag_query, "get_groq_client", lambda: fake)
    return fake


def invoke(query: str, top_k: int = 3):
    return rag_query.crag_agent.invoke(
        {
            "query": query,
            "retrieved_chunks": [],
            "evaluation": "",
            "final_answer": "",
            "top_k": top_k,
        }
    )


class TestGraphRouting:
    def test_relevant_question_stays_on_database_path(self, patched_agent):
        result = invoke("A relevant question about ML models")
        assert result["evaluation"] == "yes"
        assert result["final_answer"] == "Generated answer."
        assert len(result["retrieved_chunks"]) == 3  # DB chunks, no web fallback

    def test_irrelevant_question_routes_to_web_fallback(self, patched_agent):
        result = invoke("Who won the 2014 football world cup?")
        assert result["evaluation"] == "no"
        assert result["final_answer"] == "Generated answer."
        assert len(result["retrieved_chunks"]) == 1  # single web-fallback chunk

    def test_top_k_is_honored(self, patched_agent):
        result = invoke("A relevant question about embeddings", top_k=5)
        assert len(result["retrieved_chunks"]) == 5


class TestGraphRobustness:
    def test_evaluator_error_falls_back_to_web(self, monkeypatch):
        def evaluator_boom_only():
            return _FailingEvaluationGroq()

        monkeypatch.setattr(rag_query, "retrieve_chunks", fake_retrieve)
        monkeypatch.setattr(rag_query, "get_groq_client", evaluator_boom_only)

        result = invoke("Relevant question but Groq is down")
        assert result["evaluation"] == "no"  # evaluator failed -> defaulted to fallback
        assert result["final_answer"] == "Generated answer."  # generator still works
        assert len(result["retrieved_chunks"]) == 1  # web fallback used

    def test_empty_retrieval_routes_to_web(self, monkeypatch):
        monkeypatch.setattr(rag_query, "retrieve_chunks", lambda query, top_k=3: [])
        fake = FakeGroq()
        monkeypatch.setattr(rag_query, "get_groq_client", lambda: fake)

        result = invoke("Anything")
        assert result["evaluation"] == "no"
        assert len(result["retrieved_chunks"]) == 1

    def test_generator_failure_reports_error_not_crash(self, monkeypatch):
        monkeypatch.setattr(rag_query, "retrieve_chunks", fake_retrieve)
        monkeypatch.setattr(
            rag_query, "get_groq_client", lambda: FakeGroq() if False else _BoomGroq()
        )

        result = invoke("Relevant question")
        assert result["final_answer"].startswith("Error generating final response")


class _BoomGroq:
    """Groq client that fails on every call."""

    class _Completions:
        def create(self, messages, **kwargs):
            raise RuntimeError("connection refused")

    class _Chat:
        def __init__(self):
            self.completions = _BoomGroq._Completions()

    def chat(self):
        return self._Chat()


class _FailingEvaluationGroq(FakeGroq):
    """Fails the evaluation call but succeeds at generation."""

    class _FailingCompletions(FakeGroq._Completions):
        def create(self, messages, **kwargs):
            user = messages[-1]["content"]
            if "Answer exactly 'yes' or 'no':" in user:
                raise RuntimeError("Groq down")
            return FakeGroq._Completion("Generated answer.")

    class _Chat(FakeGroq._Chat):
        def __init__(self, owner: "_FailingEvaluationGroq"):
            self.completions = _FailingEvaluationGroq._FailingCompletions(owner)

    def __init__(self):
        self.calls: list[str] = []
        self.chat = self._Chat(self)