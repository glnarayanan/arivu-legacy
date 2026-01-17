# Entity Extraction

> **One-liner:** Automatically identify the people, companies, and technologies mentioned in your bookmarks.

## What Is It?

Entity Extraction uses AI to identify and extract **named entities** from your saved content:

- **People** — Sam Altman, Elon Musk, Ada Lovelace
- **Organizations** — OpenAI, Google, MIT
- **Technologies** — React, Kubernetes, GPT-4
- **Concepts** — Machine Learning, Serverless Architecture
- **Topics** — Climate Change, Startup Funding

These entities power the Knowledge Graph and help you discover connections across your bookmarks.

## Why It Matters

**Without Entity Extraction:**
- Your bookmarks are isolated text blobs
- Finding all articles about "OpenAI" requires manual searching
- Connections between topics are invisible

**With Entity Extraction:**
- See all mentions of "Sam Altman" across your library
- Discover you've saved 15 articles about "Kubernetes"
- The Knowledge Graph shows how topics interconnect

## How It Works

### The AI Prompt

Arivu sends content to Gemini 2.5 Flash with this instruction:

```
Extract named entities from this content. Return ONLY valid JSON.

Rules:
- Extract only explicitly mentioned entities (not inferred)
- Maximum 15 entities
- Confidence 0-1 scale based on clarity of mention
- Types: person, organization, technology, concept, topic
- Ignore common words, months, days, navigation terms
- Use canonical/full names when possible
- No duplicates

Return format:
{
  "entities": [
    {"name": "Entity Name", "type": "person", "confidence": 0.9}
  ]
}
```

### Confidence Scoring

Each entity gets a confidence score (0.0 to 1.0):

| Confidence | Meaning |
|------------|---------|
| 0.9+ | Entity is the main subject of the article |
| 0.7-0.9 | Entity is prominently mentioned |
| 0.6-0.7 | Entity is mentioned but not central |
| < 0.6 | Filtered out (not confident enough) |

**Threshold:** Only entities with **confidence ≥ 0.6** are kept.

### The Denylist

A list of 50+ common words that often get incorrectly extracted:

**Filtered out:**
- Days/months: Monday, January, etc.
- Navigation words: click, here, read, more
- Common words: the, this, that, new, update
- Vague terms: best, top, latest, recent

### Normalization

Entity names are cleaned up:
1. Convert to lowercase for deduplication
2. Trim whitespace
3. Collapse multiple spaces

```
" OpenAI  " → "openai" (for matching)
"OpenAI" → Kept as display name
```

## Real-World Example

**Article:** "How OpenAI's GPT-4 is Transforming Enterprise Software"

**Extracted entities:**

| Entity | Type | Confidence |
|--------|------|------------|
| OpenAI | organization | 0.95 |
| GPT-4 | technology | 0.95 |
| Sam Altman | person | 0.85 |
| Microsoft | organization | 0.80 |
| Large Language Models | concept | 0.90 |
| Enterprise AI | topic | 0.85 |
| Transformer Architecture | technology | 0.75 |

**Filtered out (below 0.6):**
- "the" (0.1)
- "2024" (0.3)
- "best practices" (0.5)

## Key Functions Explained

### `extract_entities_with_gemini(text_content)`
The main entity extraction function.

**Process:**
1. Take first 5000 characters (token limit)
2. Send to Gemini with structured prompt
3. Parse JSON response
4. Filter by confidence threshold (≥ 0.6)
5. Filter by denylist
6. Remove duplicates
7. Return top 15 entities

**Returns:**
```python
[
  {"name": "OpenAI", "type": "organization", "confidence": 0.95},
  {"name": "GPT-4", "type": "technology", "confidence": 0.90}
]
```

### `normalize_entity_name(name)`
Cleans entity names for consistent matching.

```python
normalize_entity_name("  OpenAI  Inc.  ")
# Returns: "openai inc."
```

### `extract_entities_and_concepts(text_content, summary_data)`
Wrapper function that:
1. Calls `extract_entities_with_gemini()`
2. Uses AI summary tags as initial concepts
3. Returns tuple of (entities, concepts)

## Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| person | Individual humans | Elon Musk, Ada Lovelace |
| organization | Companies, institutions, groups | Google, MIT, WHO |
| technology | Software, frameworks, tools | React, Docker, GPT-4 |
| concept | Abstract ideas, methodologies | Machine Learning, Agile |
| topic | Subject areas, themes | Climate Change, Fintech |

## How Entities Power Features

### Knowledge Graph
Entities create connections between bookmarks:
- Bookmark A mentions "React"
- Bookmark B mentions "React"
- → A and B are connected through the "React" entity

### Search Enhancement
Entity fields are included in hybrid search:
- Searching "Elon Musk" finds all articles mentioning him
- Even if his name isn't in the title or description

### Discovery
See what entities appear most in your library:
- "You have 23 bookmarks about Kubernetes"
- "OpenAI appears in 15% of your tech bookmarks"

## Technical Details

| Component | Value |
|-----------|-------|
| AI Model | Gemini 2.5 Flash |
| Content Limit | First 5,000 characters |
| Temperature | 0.1 (low, for consistency) |
| Max Entities | 15 per bookmark |
| Confidence Threshold | 0.6 (60%) |
| Denylist Size | 50+ common words |

## Handling AI Response

The AI returns JSON, but sometimes with markdown formatting:

```python
response_text = response.text.strip()

# Handle markdown code blocks
if response_text.startswith("```"):
    response_text = response_text.split("```")[1]
    if response_text.startswith("json"):
        response_text = response_text[4:]

data = json.loads(response_text)
```

This ensures reliable parsing even when the AI adds extra formatting.

## Comparison to Simple Approaches

### Why Not Just Use Keywords?

**Keyword extraction (TF-IDF):**
- Finds important words: "learning", "model", "training"
- No understanding of what they mean
- Can't distinguish "Apple (company)" from "apple (fruit)"

**Entity extraction (AI):**
- Understands context: "Apple announced new MacBooks"
- Knows "Apple" here means the company
- Assigns type and confidence

### Why Not Use Traditional NER?

**Traditional NER (spaCy, NLTK):**
- Fast but limited entity types
- Struggles with tech terminology
- Misses domain-specific entities

**Gemini-based extraction:**
- Understands context deeply
- Handles tech jargon well
- Provides confidence scores
- Flexible entity types
