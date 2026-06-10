---
name: text-statistics
version: 1.0.0
description: >
  Compute readability and structural statistics for a block of text: word count,
  sentence count, character count, average word length, and an approximate
  Flesch reading-ease score. Trigger when the user asks to analyze text, count
  words, measure readability, or get text statistics.
author: sarveshtalele
license: MIT
category: text-processing
tags: [text, nlp, readability, statistics]
execution:
  type: python-script
  entrypoint: scripts/main.py:run
  timeout_seconds: 15
inputs:
  - name: text
    type: string
    required: true
    description: The text to analyze.
    examples: ["The quick brown fox jumps over the lazy dog."]
outputs:
  - name: word_count
    type: integer
    description: Number of words.
  - name: sentence_count
    type: integer
    description: Number of sentences.
  - name: character_count
    type: integer
    description: Number of characters including spaces.
  - name: avg_word_length
    type: number
    description: Mean characters per word.
  - name: flesch_reading_ease
    type: number
    description: Approximate Flesch reading-ease score (higher is easier).
status: active
---

# Text Statistics Skill

Analyze a block of text and report structural and readability metrics.

## How it works

1. Tokenize the input into sentences and words.
2. Count words, sentences, and characters.
3. Estimate syllables per word to compute an approximate Flesch reading-ease score.
4. Return all metrics as a structured object.

## Usage

Call the skill with a single `text` input. The skill returns the metrics
described in the `outputs` section of the frontmatter.
