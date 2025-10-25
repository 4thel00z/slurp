"""Test hash utility functions."""

from slurp.hash import strhash


def test_strhash_consistent():
    """Test that strhash produces consistent results."""
    input_str = "test content"
    hash1 = strhash(input_str)
    hash2 = strhash(input_str)

    assert hash1 == hash2


def test_strhash_different_inputs():
    """Test that different inputs produce different hashes."""
    hash1 = strhash("content A")
    hash2 = strhash("content B")

    assert hash1 != hash2


def test_strhash_empty_string():
    """Test hashing empty string."""
    result = strhash("")
    assert result is not None
    assert len(result) > 0
