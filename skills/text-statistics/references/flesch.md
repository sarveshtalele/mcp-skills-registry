# Flesch Reading-Ease — reference

Score formula used by this skill:

```
206.835 − 1.015 × (words / sentences) − 84.6 × (syllables / words)
```

Interpretation (approximate):

| Score   | Reading level        |
|---------|----------------------|
| 90–100  | Very easy (5th grade)|
| 60–70   | Plain English        |
| 30–50   | College              |
| 0–30    | Very difficult       |

Syllables are estimated by counting vowel groups per word (silent trailing `e`
removed), so the score is approximate, not exact.
