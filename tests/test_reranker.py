import pytest
from unittest.mock import MagicMock, patch


def _make_items(*titles):
    return [{"title": t, "snippet": f"Snippet for {t}"} for t in titles]


def _mock_response(scores: list[dict]) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = f"[{', '.join(str(s).replace(chr(39), chr(34)) for s in scores)}]"
    import json
    block.text = json.dumps(scores)
    response = MagicMock()
    response.content = [block]
    return response


@patch("src.services.reranker._get_client")
def test_keeps_items_at_or_above_threshold(mock_get_client):
    items = _make_items("Stripe raises $1B", "Stripe launches new API", "Generic tech news")
    mock_get_client.return_value.messages.create.return_value = _mock_response([
        {"index": 0, "score": 9},
        {"index": 1, "score": 7},
        {"index": 2, "score": 3},
    ])

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert len(result) == 2
    assert result[0]["title"] == "Stripe raises $1B"
    assert result[1]["title"] == "Stripe launches new API"


@patch("src.services.reranker._get_client")
def test_drops_all_below_threshold(mock_get_client):
    items = _make_items("Competitor news", "Industry roundup")
    mock_get_client.return_value.messages.create.return_value = _mock_response([
        {"index": 0, "score": 4},
        {"index": 1, "score": 2},
    ])

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert result == []


@patch("src.services.reranker._get_client")
def test_preserves_original_order(mock_get_client):
    items = _make_items("A", "B", "C")
    mock_get_client.return_value.messages.create.return_value = _mock_response([
        {"index": 0, "score": 8},
        {"index": 1, "score": 3},
        {"index": 2, "score": 9},
    ])

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert [r["title"] for r in result] == ["A", "C"]


def test_empty_list_returns_empty():
    from src.services.reranker import rerank_news
    assert rerank_news("stripe", []) == []


def test_single_item_bypasses_reranker():
    from src.services.reranker import rerank_news
    items = _make_items("Only item")
    # No client call should be made
    with patch("src.services.reranker._get_client") as mock_get_client:
        result = rerank_news("stripe", items)
        mock_get_client.assert_not_called()
    assert result == items


@patch("src.services.reranker._get_client")
def test_parse_failure_returns_original(mock_get_client):
    items = _make_items("A", "B")
    block = MagicMock()
    block.type = "text"
    block.text = "not valid json at all"
    mock_get_client.return_value.messages.create.return_value.content = [block]

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert result == items


@patch("src.services.reranker._get_client")
def test_missing_index_in_scores_treated_as_zero(mock_get_client):
    items = _make_items("A", "B", "C")
    # Only returns scores for index 0 and 2; index 1 is missing
    mock_get_client.return_value.messages.create.return_value = _mock_response([
        {"index": 0, "score": 9},
        {"index": 2, "score": 8},
    ])

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert [r["title"] for r in result] == ["A", "C"]


@patch("src.services.reranker._get_client")
def test_exact_threshold_score_is_kept(mock_get_client):
    items = _make_items("Borderline item")
    # Single item bypasses reranker, so use two items
    items = _make_items("Borderline item", "Other item")
    mock_get_client.return_value.messages.create.return_value = _mock_response([
        {"index": 0, "score": 7},
        {"index": 1, "score": 6},
    ])

    from src.services.reranker import rerank_news
    result = rerank_news("stripe", items)

    assert len(result) == 1
    assert result[0]["title"] == "Borderline item"
