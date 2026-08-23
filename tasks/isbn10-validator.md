# Task: ISBN-10 Validator

Complete this task. Return your answer EXACTLY in this format:

```
CODE:
```python
<your python code>
```
EXPLANATION:
<one paragraph>
EDGE_CASE:
<one sentence>
```

The task:

1. Write a Python function `is_valid_isbn10(code: str) -> bool` that validates an ISBN-10 string (allow hyphens), including the checksum: digits d1..d9 plus a check digit, weighted sum of d_i * (10-i) for i in 0..9 must be divisible by 11. The check digit may be 'X' (value 10) in the last position.
2. Explain in one paragraph how the checksum works and why it catches transposition errors.
3. List exactly one edge case most implementations get wrong and how your code handles it.

## Test suite (verify_codes.py)

| Input | Expected | What it checks |
|---|---|---|
| `0-306-40615-2` | True | classic valid (hyphenated) |
| `0306406152` | True | valid, no hyphens |
| `0-8044-2957-X` | True | 'X' check digit |
| `0-306-40615-3` | False | wrong check digit |
| `X123456789` | False | 'X' in first position |
| `12345678X9` | False | 'X' not in last position |
| `0-306-4061` | False | wrong length |
| `0-306-40615-2x` | False | lowercase x (extra char) |
| `0-306-40615-2 ` | True | trailing whitespace (bonus robustness) |
