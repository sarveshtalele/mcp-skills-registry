# text-statistics

Compute readability and structural statistics for a block of text.

## Inputs

| name | type   | required | description           |
|------|--------|----------|-----------------------|
| text | string | yes      | The text to analyze.  |

## Outputs

`word_count`, `sentence_count`, `character_count`, `avg_word_length`,
`flesch_reading_ease`.

## Run locally

```bash
echo '{"text": "The quick brown fox jumps over the lazy dog."}' \
  | python scripts/main.py   # via the registry runner, or:
python -c "from scripts.main import run; print(run({'text': 'Hello world.'}))"
```

## Via the registry API

```bash
curl -X POST http://localhost:7860/api/v1/skills/text-statistics/execute \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"text": "The quick brown fox jumps over the lazy dog."}}'
```
