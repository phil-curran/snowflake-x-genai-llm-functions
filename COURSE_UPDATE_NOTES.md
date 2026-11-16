# Snowflake x GenAI: LLM Functions (SXGA2): course update notes

Verified by running every lesson in `lesson_01` to `lesson_07` on a current paid account (AWS US West 2), 2026-11-14.
These add to, and confirm, the earlier written audit (`sxga2-llm-functions_audit_2026-11-10.md`). Each item is also an
in-line "Course update needed" or "Audit note" cell in the lesson notebooks. This course has no DORA grading.

## Blockers (the step cannot be done as written)

| # | Where | Finding | Verified result | Replacement used |
|---|---|---|---|---|
| 1 | Lessons 2, 3, 6, wrap-up | The course teaches `SNOWFLAKE.CORTEX.TRANSLATE`, `SENTIMENT`, `SUMMARIZE` | Blocked on new accounts: "New accounts are blocked from using legacy SNOWFLAKE.CORTEX functions" | `AI_TRANSLATE`, `AI_SENTIMENT`, `AI_SUMMARIZE` |
| 2 | Lesson 3 | `AI_SENTIMENT` is not a drop-in for `SENTIMENT` | Returns `{"categories":[{"name":"overall","sentiment":"negative"}]}` (a label), not a score from -1 to 1 | Show the label (`:categories[0]:sentiment`); the page premise, the "predict the number" exercise and all later score use must be rewritten |
| 3 | Lesson 3 | The API function uses `runtime_version=3.9` | "Python runtime version 3.9 is decommissioned" | 3.12 |
| 4 | Lesson 3 | The API key is typed into the function (`api_key = 'YOUR API KEY'`) | Works, but the key sits in the function text and in query history | Snowflake SECRET + `_snowflake.get_generic_secret_string`; the secret needs `USAGE` **and `READ`** for the function owner, and the integration needs `allowed_authentication_secrets` |
| 5 | Lessons 4-6 | Document AI (role `DOCUMENT_INTELLIGENCE_CREATOR`, "build a model", Train Model, `<model>!PREDICT`) | Decommissioned 2026-03-16 (BCR-2156). `CREATE SNOWFLAKE.ML.DOCUMENT_INTELLIGENCE` no longer parses. The database role still exists | `AI_EXTRACT` on staged PDFs, see #6 |
| 6 | Lessons 4-6 | `AI_EXTRACT` cannot be asked the `lyrics` question | For every copyrighted lyric sheet the answer is `AI_EXTRACT failed: the model refused to answer` with `response: null`, even when lyrics is the only question. Only the public-domain "Mary Had A Little Lamb" worked | Six questions to `AI_EXTRACT`, lyrics text from `AI_PARSE_DOCUMENT` (OCR mode), combined in one function named `LYRICS_EXTRACTOR` |

## Major (misleading or wrong)

| # | Where | Finding |
|---|---|---|
| 7 | Lesson 3 | "Trial accounts MUST enter a credit card" for external access. The earlier audit found trials cannot use external access at all. On this paid account it works. |
| 8 | Lesson 5 | The course code reads `@LYRICS_PDF` but the stage the learner just created is `lyrics_pdfs` (the screenshot LLMM_168 uses `@LYRICS_PDFS`). |
| 9 | Lessons 4-5 | No confidence scores exist with `AI_EXTRACT`: remove the score columns, the "approve to make it 1.00" and "learns from the feedback loop" text, and "20 training cases". |
| 10 | Lessons 5-6 | The parsing selects and `PARSED_SONG_DATA` view read Document AI's shape (`json:song_title[0].value`). `AI_EXTRACT` stores `{error, response:{...}}`, so they return NULLs until rewritten. |
| 11 | Lesson 6 | `DOC_AI_ROLE` only gets `CREATE SCHEMA, MODIFY, USAGE` on DOC_AI_DB, so it cannot grant `USAGE` on the database to SYSADMIN. The course screenshot has ACCOUNTADMIN do it. |
| 12 | Wrap-up | "Korean and Japanese PDFs did not fare as well" is no longer true: both BTS PDFs extract correctly (title, artist, full lyrics in Hangul and Japanese). |
| 13 | Wrap-up | `AI_SUMMARIZE(AI_TRANSLATE(...))` in one SELECT fails with "Non-SQL UDF is not supported inside lambda expression". The translation has to be materialized (temp table / CTAS) first. |
| 14 | Lesson 2 | The "`translate()` without a schema is a different function" trap only exists for the legacy name. With `AI_TRANSLATE` there is nothing to confuse; the page and quiz can go. |

## Recency

- "LLM functions" is now "Cortex AI Functions"; the lab screenshots highlight the legacy function.
- Quiz answer `AI_EMBED_TEXT_768` does not exist (the account has `AI_EMBED_768`).
- Checklist link `learn.snowflake.com/en/courses/uni-fod-sxga/` returns 404 (the course lives at `.../OD-SXGA/`).
- GenAI animation commentary (Bing Image Creator, aitubo.com, "our new AI CEO") is dated.

## What the notebooks do about each

Course code that no longer works runs **as written** and reports its error (a "protected" cell), followed by a
labelled **Substitute** cell using the current function. Nothing that fails is hidden.

## Setup the notebooks need that the course does not mention

- A Snowflake secret holding your own API Ninjas key (never committed): see `dora/account_setup.ipynb`.
- `DOC_AI_ROLE` needs `USAGE` on UTIL_DB and `READ` on the Downloads stand-in stage to load the PDFs
  (only because the learner's Downloads folder is simulated by a stage).
- The sample PDFs are in `data/` with the file names the course gives (Rise truncates asset names).
