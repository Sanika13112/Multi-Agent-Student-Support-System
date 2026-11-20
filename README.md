# StudyMate AI: Multi-Agent Student Support System

StudyMate AI is a study assistant for engineering students that runs on your own computer. Upload notes, a lecture recording or a college notice, and it produces revision notes, answers questions with page references, builds quizzes, translates notices and plans your study. A local LLM (Qwen via Ollama) does the generation; classic NLP (NLTK, scikit-learn, fastText) does the text processing.

B.Tech CSE (AIML) · NLP course project.

---

## Features

| Module | What it does | Input |
|---|---|---|
| **AI Assistant** | Chat. A supervisor agent routes each message to the right agent (study explanation, career guidance, …) | Your question |
| **QuickNotes** | Turns a PDF or text file into structured revision notes, keeping diagrams | PDF or TXT |
| **VoiceSnap** | Transcribes a lecture recording (faster-whisper) and turns it into notes | Audio file |
| **AskAway** | Answers questions about your document and shows the pages each answer came from (RAG) | PDF or TXT |
| **BrainCheck** | Generates MCQs, scores them, keeps your history and suggests a study plan. After each quiz, students rate it and give feedback, which is analysed with sentiment analysis and shown next to their performance | Subject and topic |
| **Notice Translator** | Reads a notice (OCR for photos and scanned PDFs, direct text for PDFs and Word files), detects English / Hindi / Marathi, extracts dates, times, deadlines, venues and contacts, and translates | JPG, PNG, PDF, DOCX |
| **Career Guidance** | Career paths, skill gaps and a learning roadmap | Your profile |
| **NLP Pipeline** | Runs one document through every NLP stage (CO1–CO4) and shows each stage's output | PDF, TXT or pasted text |

## How it maps to the project rubric

The **NLP Pipeline** page demonstrates all four rubric rows on one document. See **[RUBRIC.md](RUBRIC.md)** for the stage-by-stage mapping, measured results and viva notes.

| Rubric row | CO | Marks | Where |
|---|---|---|---|
| Text extraction, preprocessing, cleaning, vectorization | CO1 | 7 | Pipeline stages 1–4 · `nlp/preprocess.py` |
| Sentiment analysis + information extraction, with evaluation | CO2 | 8 | Stages 5–7 · **BrainCheck student feedback** · `nlp/sentiment.py`, `nlp/feedback_analysis.py`, `nlp/information_extraction.py`, `nlp/evaluation.py` |
| Topic modeling / multilingual NLP with a cloud AI service | CO3 | 7 | Stages 8, 9, 11 · `nlp/topic_modeling.py`, `nlp/multilingual.py`, Notice Translator |
| Generative AI, prompt engineering, integration, working demo | CO4 | 8 | Stage 10 · whole app · `modules/common/ai_client.py` |

---

## Tech stack

- **Backend:** Python 3.11, Flask
- **Frontend:** HTML, CSS, JavaScript (Jinja templates; marked, Mermaid and DOMPurify bundled locally)
- **LLM:** Ollama running `qwen2.5:1.5b` locally
- **NLP:**
  - NLTK: tokenizing, stop words, Porter stemmer, VADER sentiment
  - scikit-learn: TF-IDF, LDA, evaluation metrics
  - fastText `lid.176`: language identification
- **Retrieval (AskAway):** `all-MiniLM-L6-v2` embeddings (sentence-transformers) + BM25 keyword index
- **Speech / OCR:** faster-whisper (VoiceSnap), EasyOCR (Notice Translator)
- **Documents:** pypdf, PyMuPDF
- **Database:** MySQL (BrainCheck quiz history)
- **Cloud service:** MyMemory Translation API (translation only)

## Project structure

```
Multi-Agent-Student-Support-System/
├── app.py                     Flask app: page routes and APIs
├── run_pipeline.py            Run the NLP pipeline from the command line
├── RUBRIC.md                  Rubric mapping and viva notes
├── agents/supervisor/         Supervisor: rule router + LLM router
├── modules/
│   ├── common/                Ollama client, document loader, database, utilities
│   ├── quick_notes/           QuickNotes (formatter, diagram extraction)
│   ├── ask_away/              AskAway RAG chatbot
│   ├── voice_snap/            VoiceSnap transcription
│   └── notice_translator/     OCR, language detection, translation
├── nlp/
│   ├── preprocess.py          Cleaning, tokenizing, stop words, TF-IDF        (CO1)
│   ├── sentiment.py           VADER sentiment                                  (CO2)
│   ├── feedback_analysis.py   Quiz feedback: sentiment, aspects, vs. scores    (CO2)
│   ├── information_extraction.py  Definitions, acronyms, key terms            (CO2)
│   ├── evaluation.py          Accuracy, precision, recall, F1                  (CO2)
│   ├── topic_modeling.py      LDA topics, TF-IDF keywords                      (CO3)
│   ├── multilingual.py        fastText language detection, cloud translation  (CO3)
│   └── pipeline.py            End-to-end pipeline, CO1–CO4                     (all)
├── templates/  static/        Pages, CSS, JavaScript
├── models/lid.176.ftz         fastText language-ID model
├── data/                      Sample notes (DAA Unit 5 PDF)
├── Notebooks/                 Experiments per module
└── tests/                     Unit tests and check scripts
```

---

## Setup (Windows)

### 1. Install the tools

- **Python 3.11**: `winget install Python.Python.3.11`
- **Ollama**: from https://ollama.com, then download the model:
  ```bat
  ollama pull qwen2.5:1.5b
  ```
- **MySQL Server 8+**: only needed for BrainCheck history.

### 2. Get the code and install packages

```bat
git clone https://github.com/Sanika13112/Multi-Agent-Student-Support-System.git
cd Multi-Agent-Student-Support-System
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip install ollama numpy sentence-transformers faster-whisper easyocr fasttext-wheel pymupdf
```

The second `pip install` line adds packages the modules import that are not yet in `requirements.txt`.

### 3. Download NLTK data (once)

```bat
python -c "import nltk; [nltk.download(p) for p in ('stopwords','vader_lexicon','punkt_tab')]"
```

### 4. Set up the database (for BrainCheck history)

In MySQL Workbench or the `mysql` client:

```sql
CREATE DATABASE IF NOT EXISTS studymate_db;
USE studymate_db;

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    subject           VARCHAR(150) NOT NULL,
    topic             VARCHAR(200) NOT NULL,
    difficulty        VARCHAR(20)  NOT NULL,
    total_questions   INT NOT NULL,
    correct_answers   INT NOT NULL,
    incorrect_answers INT NOT NULL,
    unanswered        INT NOT NULL,
    score_percentage  DECIMAL(5,2) NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Then set your MySQL host, user, password and **port** in `DB_CONFIG` in `modules/common/database.py`. Don't commit a real password to GitHub.

The `quiz_feedback` table (student feedback) is created automatically the first time feedback is saved or loaded.

---

## Run

Start Ollama (open the Ollama app), then:

```bat
venv\Scripts\activate
python app.py
```

| Page | URL |
|---|---|
| Dashboard | http://127.0.0.1:5000/ |
| AI Assistant | http://127.0.0.1:5000/assistant |
| QuickNotes | http://127.0.0.1:5000/quick-notes |
| VoiceSnap | http://127.0.0.1:5000/voice-snap |
| AskAway | http://127.0.0.1:5000/ask-away |
| BrainCheck | http://127.0.0.1:5000/brain-check |
| Notice Translator | http://127.0.0.1:5000/notice-translator |
| Career Guidance | http://127.0.0.1:5000/career-guidance |
| **NLP Pipeline** | http://127.0.0.1:5000/nlp-pipeline |
| Health check | http://127.0.0.1:5000/api/health |

### NLP Pipeline from the command line

```bat
python run_pipeline.py data\DAA_Unit5_Computational_Complexity.pdf --translate mr
python run_pipeline.py my_notes.txt --no-llm --topics 4
```

This prints one line per stage and saves `reports\<name>_pipeline.md` and `.json`.

| Option | Meaning |
|---|---|
| `--translate hi` / `--translate mr` | Translate the LLM summary to Hindi or Marathi (needs internet) |
| `--no-llm` | Skip the Ollama step |
| `--topics N` | Number of LDA topics (2–15) |

### NLP APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/nlp-pipeline/run` | Full pipeline: form fields `file` or `text`, `use_llm`, `translate_to`, `num_topics` |
| POST | `/api/sentiment/analyze` | Sentiment of a text (`mode`: `overall` or `sentences`) |
| GET | `/api/sentiment/evaluate` | Sentiment metrics on the built-in labelled set |
| POST | `/api/topic-modeling/extract` | LDA topics |
| POST | `/api/topic-modeling/keywords` | TF-IDF keywords |
| POST | `/api/brain-check/feedback` | Save quiz feedback (`attempt_id`, `feedback_text`, optional `rating` 1–5) and return its sentiment and aspects |
| GET | `/api/brain-check/feedback-summary` | All feedback with sentiment split, score by sentiment, aspects and accuracy vs star ratings |

---

## Tests

```bat
python -m unittest tests.test_pipeline tests.test_information_extraction tests.test_feedback_analysis tests.test_notice_text tests.test_preprocessing
```

The pipeline tests replace Ollama and the translator with fakes, so they run offline. Other files in `tests/` cover the routers, formatter, document loader and OCR; some need Ollama, EasyOCR or MySQL running.

## Measured results

| Measure | Result |
|---|---|
| Sentiment (VADER) on 24 labelled sentences | Accuracy 0.917, F1 0.917 |
| Definition extraction on 12 labelled samples | Precision 1.00, recall 0.83, F1 0.91 |
| Acronym extraction on 12 labelled samples | Precision 0.75, recall 0.75, F1 0.75 |
| LDA on the sample DAA PDF (5 topics) | Perplexity 121.3 |

Details, including known misses, are in [RUBRIC.md](RUBRIC.md).

## Privacy

Almost everything runs on your computer: the LLM, embeddings, speech-to-text, OCR and all NLP. The one exception is **translation** (Notice Translator and pipeline stage 11), which sends the text to the MyMemory cloud API. Set `MYMEMORY_EMAIL` to raise MyMemory's free daily limit.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Local AI offline", or LLM stage fails | Open Ollama; check `ollama list` shows `qwen2.5:1.5b` |
| `LookupError: Resource stopwords / vader_lexicon / punkt_tab not found` | Run the NLTK download command in setup step 3 |
| "Could not connect to the MySQL database" | Check that MySQL is running and that `DB_CONFIG` (especially `port`) matches your server |
| Translation fails | Needs internet; MyMemory also has a daily limit |
| fastText "Unable to avoid copy while creating an array" | Fixed: language detection uses `nlp.multilingual.fasttext_predict`, which works with NumPy 1 and 2 |
| AskAway is slow the first time | The embedding model downloads and loads once |
| Notice Translator: "fastText is not installed" | `python -m pip install fasttext-wheel` |
| Notice Translator: "EasyOCR is not installed" | `python -m pip install easyocr` (needed for photos and scanned PDFs only; text PDFs and Word files work without it) |
| Notice Translator is slow on the first photo | EasyOCR downloads its models (about 100 MB) once |
| Notice Translator: old `.doc` file rejected | Open it in Word and save it as `.docx` or PDF |
