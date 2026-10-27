"""Reject ambiguous object fields before validating research JSONL records."""

import json


def parse_unique_json(serialized: str | bytes):
    """Parse one JSON value, rejecting repeated keys at every object depth."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field in research input")
            result[key] = value
        return result

    return json.loads(serialized, object_pairs_hook=unique_object)
