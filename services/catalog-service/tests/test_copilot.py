from __future__ import annotations

from app.copilot import classify_intent


def test_shopping_keywords_are_in_scope():
    assert classify_intent("Why did you recommend BUY for this product?")
    assert classify_intent("Which reviews look fake?")
    assert classify_intent("Compare this seller with alternatives.")
    assert classify_intent("Should I wait before buying?")


def test_short_question_words_are_allowed_as_followups():
    assert classify_intent("Why?")
    assert classify_intent("What about shipping time?")


def test_clearly_unrelated_requests_are_out_of_scope():
    assert not classify_intent("Write me a poem about the ocean.")
    assert not classify_intent("Tell me a joke.")
    assert not classify_intent("Translate this sentence into French.")
