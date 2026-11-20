# Project Demonstration Rubric: where each criterion is in StudyMate AI

Rubric: **D. Project Demonstration Assessment, 30 marks (CO1–CO4)**.

The **NLP Pipeline** (`nlp/pipeline.py`) runs one study document through every stage below, in order, and shows each stage's real output grouped by CO. Use it as the backbone of the demo.

| # | Criterion | CO | Marks | Pipeline stages | Main code |
|---|---|---|---|---|---|
| 1 | Text extraction, preprocessing, cleaning and vectorization of unstructured data | CO1 | 7 | 1 Text extraction · 2 Cleaning · 3 Tokenization, stop words, stemming · 4 TF-IDF | `modules/common/document_loader.py`, `nlp/preprocess.py` |
| 2 | Implementation and evaluation of sentiment analysis and information extraction | CO2 | 8 | 5 Sentiment · 6 Information extraction · 7 Evaluation · **BrainCheck student feedback** | `nlp/sentiment.py`, `nlp/feedback_analysis.py`, `nlp/information_extraction.py`, `nlp/evaluation.py` |
| 3 | Topic modeling or multilingual NLP with NLP techniques and cloud-based AI services | CO3 | 7 | 8 LDA topics · 9 Language detection · 11 Cloud translation | `nlp/topic_modeling.py`, `nlp/multilingual.py`, `modules/notice_translator/` |
| 4 | Generative AI/LLM application, prompt engineering, integration, working demo | CO4 | 8 | 10 LLM summary with an engineered prompt | `nlp/pipeline.py` (prompt), `modules/common/ai_client.py` (Ollama) |

## How to run it

**Web page:** start the app as usual (`python app.py`), open **http://127.0.0.1:5000/nlp-pipeline** (sidebar → *Project demo* → *NLP Pipeline*), upload a PDF/TXT and click **Run pipeline**. Download buttons save the report as Markdown or JSON.

**Command line** (writes `reports/<name>_pipeline.md` and `.json`):

```bat
python run_pipeline.py data\DAA_Unit5_Computational_Complexity.pdf
python run_pipeline.py data\DAA_Unit5_Computational_Complexity.pdf --translate mr
python run_pipeline.py notes.txt --no-llm --topics 4
```

**Tests:**

```bat
python -m unittest tests.test_information_extraction tests.test_pipeline tests.test_preprocessing
```

**Requirements:** no new packages. One-time NLTK data download, if not done already:
`python -c "import nltk; [nltk.download(p) for p in ('stopwords','vader_lexicon','punkt_tab')]"`

- Stage 10 needs **Ollama** running with the project's Qwen model (`modules/common/ai_client.py` → `MODEL_NAME`).
- Stage 11 needs **internet** (MyMemory).
- If either is unavailable, that stage shows **Failed** with the real reason; it never shows invented output.

## Measured results (`data/DAA_Unit5_Computational_Complexity.pdf`, 15 pages)

| Stage | Result |
|---|---|
| 1 Extraction | 15 pages, 10,753 characters, 1,979 words |
| 3 Tokenization | 1,940 tokens → 1,388 after stop words → 1,126 after 1-letter tokens → 323 unique stems |
| 4 TF-IDF | 22 segments × 1,056 terms, 93.0% sparse; top terms *np, problem, polynomial, sat* |
| 5 Sentiment | 47.8% neutral, 36.1% positive, 16.1% negative (factual notes are mostly neutral) |
| 6 Extraction | 3 definitions, 1 acronym (SAT), 15 key terms, 5 Big-O expressions |
| 7 Evaluation | Sentiment: accuracy 0.917, F1 0.917 (24 labelled sentences). Definitions: P 1.00, R 0.83, F1 0.91. Acronyms: P 0.75, R 0.75, F1 0.75 (12 labelled samples) |
| 8 LDA | 5 topics, perplexity 121.3 (e.g. *tsp, vertex, cover*; *easy, problems, tractable*) |
| 9 Language | English, fastText confidence 0.89 |

Stages 10 and 11 were not run in the build environment (no Ollama, no internet). Run them on your laptop for the demo.

## Viva notes

### CO1: from a PDF to numbers

- **Extraction:** `pypdf` reads each page's text layer. Scanned PDFs have no text layer and are rejected with a message.
- **Cleaning:** lower-case, then keep only `a–z 0–9` and spaces, then collapse whitespace (`nlp/preprocess.py: clean_text`).
- **Tokenization and stop words:** NLTK `word_tokenize`; stop words removed except negations and question words (*not, why, how…*), because they change meaning. 1-letter tokens are dropped; they come from letter-spaced slide titles like "D E S I G N".
- **Stemming:** Porter stemmer (*complexity → complex*, *polynomial → polynomi*) so word forms count together.
- **Vectorization:** TF-IDF on ~500-character segments with single words and word pairs.
  - TF-IDF = term frequency × inverse document frequency: a word scores high when it is frequent in one segment but rare across the others.
  - The matrix is ~93% zeros (sparse), which is normal for text.

### CO2: sentiment, extraction and how we know they work

- **Sentiment:** NLTK VADER, a lexicon- and rule-based model. Its compound score runs from −1 to +1: ≥ 0.05 is Positive, ≤ −0.05 is Negative, otherwise Neutral.
- Slides often have no full stops, so the pipeline first uses a line-aware sentence splitter (headings are kept separate).
- **Information extraction** (`nlp/information_extraction.py`), rule-based so every result is explainable:
  - Definitions: patterns "*X is/are/refers to/means …*" and "*… is called X*". Terms that start with pronouns, or are really lists ("*X and Y are*") or clauses, are rejected.
  - Acronyms: the **Schwartz & Hearst (2003)** algorithm. It walks backwards through the acronym and the preceding words, so *D**a**ta**B**ase **M**anagement **S**ystem → DBMS* matches.
  - Key terms (TF-IDF over sentences), Big-O expressions (regex) and dates/years.
- **Evaluation:**
  - Sentiment is scored on 24 labelled sentences: accuracy, precision, recall, F1, confusion matrix.
  - Extraction is scored on 12 labelled samples with precision/recall/F1.
  - Known misses, kept on purpose so the score is honest:
    - "*A greedy algorithm makes the locally best choice*" has no definition verb, so it is not caught.
    - SAT expands to "*Satisfiability*" instead of "*Boolean satisfiability*".

### CO2 in BrainCheck: student feedback and performance

Sentiment fits opinions better than study notes, so BrainCheck collects real student opinions:

1. After a quiz, the student gives **1–5 stars** and writes feedback (BrainCheck → results → *How was this quiz?*).
2. `nlp/feedback_analysis.py` runs **VADER** on the text and finds the **aspects** it mentions (Difficulty, Timer, Questions, Explanations, Topic coverage) using a keyword lexicon. Each aspect gets the sentiment of the sentences that mention it: **aspect-based sentiment analysis**.
3. The result is stored in MySQL table `quiz_feedback`, linked to the quiz attempt and its score.
4. The **Student Feedback & Sentiment** card in *Student Performance* shows:
   - the sentiment split and the **average quiz score per sentiment**;
   - the **Pearson correlation** between score and sentiment (do students who score higher write happier feedback?);
   - how often each aspect is mentioned, and how positively;
   - **evaluation on real data:** VADER vs each student's own star rating (4–5★ = Positive, 3★ = Neutral, 1–2★ = Negative), with accuracy, precision, recall, F1 and a confusion matrix.

Known VADER limits this exposes (good viva points):
- *"the timer was too short"* scores neutral, because VADER has no word for "too short" being bad.
- *"Okay quiz."* scores positive while the student gave 3 stars.

### CO3: topics and languages

- **LDA:** each segment is a mixture of topics, and each topic is a distribution over words. Built on a bag-of-words count matrix. **Perplexity** measures how well the model predicts the text (lower is better, comparable only on the same data).
- **Language detection:** the offline **fastText lid.176** model (176 languages) separates English, Hindi and Marathi even though Hindi and Marathi share the Devanagari script. Without fastText, the code falls back to script counting and says so.
- **Cloud AI service:** the **MyMemory Translation API** translates the LLM summary into Hindi or Marathi (stage 11), and the Notice Translator page uses the same service.

### CO4: the LLM and prompt engineering

The local model (Qwen via Ollama) gets a prompt built from the earlier stages. The techniques used, all visible under *Show the exact prompt* on the page:

1. **Role prompting:** the system prompt makes the model a careful teaching assistant.
2. **Grounding:** "use ONLY the CONTEXT"; anything missing must be called "Not covered in the notes".
3. **Context from the NLP pipeline:** TF-IDF key terms, LDA topics and extracted definitions are placed in the prompt.
4. **Output format:** fixed headings *Summary / Key points / Exam question*.
5. **Low temperature (0.3):** factual, repeatable answers.

The output is then checked automatically:
- **Format followed?** All three headings must be present.
- **Grounding %:** how many of the document's top key terms the summary uses.

This is a simple, explainable way to evaluate generated text.

## Files added or changed for this

- **New:**
  - `nlp/pipeline.py`, `nlp/information_extraction.py`, `nlp/multilingual.py`, `run_pipeline.py`
  - `templates/nlp_pipeline.html`, `static/js/nlp_pipeline.js`, `static/css/pages/nlp-pipeline.css`
  - `tests/test_pipeline.py`, `tests/test_information_extraction.py`, `RUBRIC.md`
  - BrainCheck feedback: `nlp/feedback_analysis.py`, `static/js/brain_check_feedback.js`, `tests/test_feedback_analysis.py`
- **Changed:**
  - `app.py`: `/nlp-pipeline` page and `POST /api/nlp-pipeline/run`; BrainCheck feedback APIs `POST /api/brain-check/feedback` and `GET /api/brain-check/feedback-summary`.
  - `templates/brain_check.html`, `static/js/brain_check.js`, `static/css/pages/brain-check.css`: feedback form, save events and dashboard card.
  - `templates/config/navigation.html`: sidebar entry.
  - `static/css/main.css`: page stylesheet import.
  - `modules/notice_translator/__init__.py`: loads the OCR service only when it is used, so text translation doesn't load EasyOCR.
  - `modules/notice_translator/service.py` and `tests/test_language_detection.py`: fastText predictions now work with NumPy 2 (previously failed with *"Unable to avoid copy while creating an array"*).
