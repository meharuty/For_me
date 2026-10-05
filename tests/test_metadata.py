"""Metadata block parsing."""
import pytest

from src.parser.metadata import MetadataParser


def test_valid_and_empty() -> None:
    assert MetadataParser.parse("[zone=normal color=red]") == {
        "zone": "normal", "color": "red"}
    assert MetadataParser.parse("[]") == {}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("zone=normal", "enclosed in brackets"),
        ("[zone=]", "value cannot be empty"),
        ("[=normal]", "key cannot be empty"),
        ("[zone=a=b]", "Invalid metadata format"),
        ("[zone]", "Invalid metadata format"),
        ("[color=red color=blue]", "Duplicate metadata key"),
    ],
)
def test_invalid(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        MetadataParser.parse(text)


def test_known_keys() -> None:
    MetadataParser.ensure_known_keys({"zone": "x"}, {"zone"}, "a hub")
    with pytest.raises(ValueError, match="Unknown metadata key"):
        MetadataParser.ensure_known_keys({"zoen": "x"}, {"zone"}, "a hub")
