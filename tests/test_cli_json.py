#!/usr/bin/env python3
"""
Unit tests for fmem CLI --format and --min-score flags.

Tests the JSON output format and score filtering functionality.
"""

import json
import subprocess
import unittest


def extract_json_from_output(output: str) -> str:
    """Extract JSON array from output that may contain log messages.
    
    The CLI logs to stdout during initialization, but the final output
    is a JSON array. Find the start of the array and extract it.
    """
    # Find the start of the JSON array
    start = output.rfind('[')
    if start == -1:
        return output  # No array found, return as-is
    
    # Find the matching closing bracket
    depth = 0
    for i, c in enumerate(output[start:], start):
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return output[start:i+1]
    
    return output[start:]  # Incomplete, return what we have


class TestCliJsonFormat(unittest.TestCase):
    """Test CLI --format json flag."""
    
    def test_format_json_returns_valid_json_array(self):
        """Test that --format json returns a valid JSON array."""
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "test", "--format", "json", "--top-k", "3"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        # Extract JSON from output (logs go to stdout too)
        json_output = extract_json_from_output(result.stdout)
        
        # Should parse as valid JSON
        try:
            data = json.loads(json_output)
            self.assertIsInstance(data, list)
        except json.JSONDecodeError as e:
            self.fail(f"Output is not valid JSON: {e}\nOutput: {json_output}")
    
    def test_format_json_result_schema(self):
        """Test that JSON results have required fields."""
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "1"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_output = extract_json_from_output(result.stdout)
        data = json.loads(json_output)
        
        # If results exist, check schema
        if len(data) > 0:
            required_fields = ["filepath", "score", "content", "heading", "source"]
            for field in required_fields:
                self.assertIn(field, data[0], f"Missing required field: {field}")
    
    def test_format_json_adaptive_truncation(self):
        """Test that adaptive mode truncates content based on score."""
        result_low = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "3"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_output = extract_json_from_output(result_low.stdout)
        data = json.loads(json_output)
        
        if len(data) >= 2:
            # Higher score should have >= content length than lower score
            # (adaptive mode gives more chars to higher scores)
            high_score_len = len(data[0]["content"])
            low_score_len = len(data[-1]["content"])
            self.assertGreaterEqual(high_score_len, low_score_len,
                f"Higher score result ({data[0]['score']:.3f}) should have >= content length "
                f"than lower score ({data[-1]['score']:.3f})")
    
    def test_format_json_fixed_truncation(self):
        """Test that --content-mode fixed applies uniform limit."""
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "3",
             "--max-content", "100", "--content-mode", "fixed"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_output = extract_json_from_output(result.stdout)
        data = json.loads(json_output)
        
        # All results should have content <= 103 chars (100 + "...")
        for item in data:
            self.assertLessEqual(len(item["content"]), 103,
                f"Fixed mode content too long: {len(item['content'])} chars")
    
    def test_format_text_returns_human_readable(self):
        """Test that --format text (default) returns human-readable output."""
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--top-k", "1"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        # Text format should NOT be valid JSON
        try:
            json.loads(result.stdout)
            # If it parsed, it might be empty array - that's okay
            if result.stdout.strip() == "[]":
                return
            # Otherwise, text format shouldn't be JSON
            self.fail("Text format should not return valid JSON (unless empty)")
        except json.JSONDecodeError:
            pass  # Expected - text format is not JSON
        
        # Text format should contain "Score:" if results exist
        if "No results found" not in result.stdout and result.stdout.strip():
            self.assertIn("Score:", result.stdout)
    
    def test_default_format_is_text(self):
        """Test that default format is text (human-readable)."""
        # Without --format flag - extract just the result portion
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--top-k", "1"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        # Should be same as --format text
        result_explicit = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--top-k", "1", "--format", "text"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        # Compare the output lines after logs (logs contain timestamps that differ)
        # Filter out log lines (contain " - ") and compare the rest
        def filter_logs(output):
            lines = output.split('\n')
            return '\n'.join([l for l in lines if ' - ' not in l and not l.startswith('2026-')])
        
        self.assertEqual(filter_logs(result.stdout), filter_logs(result_explicit.stdout))


class TestCliMinScore(unittest.TestCase):
    """Test CLI --min-score flag."""
    
    def test_min_score_filters_low_scores(self):
        """Test that --min-score filters out results below threshold."""
        # Get all results first
        result_all = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "10"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_all = extract_json_from_output(result_all.stdout)
        data_all = json.loads(json_all)
        
        if len(data_all) == 0:
            self.skipTest("No results in index for testing")
        
        # Get results with min-score filter
        result_filtered = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "10", "--min-score", "0.5"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_filtered = extract_json_from_output(result_filtered.stdout)
        data_filtered = json.loads(json_filtered)
        
        # All filtered results should have score >= 0.5
        for item in data_filtered:
            self.assertGreaterEqual(item["score"], 0.5, 
                f"Result with score {item['score']} should have been filtered out")
        
        # Filtered count should be <= unfiltered count
        self.assertLessEqual(len(data_filtered), len(data_all))
    
    def test_min_score_zero_returns_all(self):
        """Test that --min-score 0.0 returns all results (same as no filter)."""
        result_no_filter = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "5"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        result_zero = subprocess.run(
            ["python3", "-m", "fmem", "search", "pix", "--format", "json", "--top-k", "5", "--min-score", "0.0"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        json_no_filter = extract_json_from_output(result_no_filter.stdout)
        json_zero = extract_json_from_output(result_zero.stdout)
        
        data_no_filter = json.loads(json_no_filter)
        data_zero = json.loads(json_zero)
        
        self.assertEqual(len(data_no_filter), len(data_zero))


class TestCliErrors(unittest.TestCase):
    """Test CLI error handling."""
    
    def test_invalid_format_rejected(self):
        """Test that invalid format value is rejected."""
        result = subprocess.run(
            ["python3", "-m", "fmem", "search", "test", "--format", "invalid"],
            capture_output=True,
            text=True,
            cwd="/home/luis/.openclaw/workspace/projects/fmem"
        )
        
        # Should exit with error
        self.assertNotEqual(result.returncode, 0)
        # Error should mention invalid choice
        self.assertIn("invalid choice", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()