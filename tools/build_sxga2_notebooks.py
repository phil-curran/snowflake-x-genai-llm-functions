"""Build the Snowflake x GenAI: LLM Functions (SXGA2) lesson notebooks for Snowflake Workspaces.

Usage: python3 build_sxga2_notebooks.py
Output: ../notebooks/sxga2_llm_functions/  (7 lesson notebooks, dora/account_setup, data/)

Course code is read verbatim from the Rise export. Role/warehouse names are swapped for isolation variables:
    ACCOUNTADMIN -> {{ADMIN_ROLE}}     SYSADMIN -> {{SYSADMIN_ROLE}}     COMPUTE_WH -> {{WAREHOUSE}}
Where course code no longer works in a current account (legacy SNOWFLAKE.CORTEX functions, Python 3.9,
Document AI), the course code is run as written (errors are reported, not hidden) and followed by a
labelled substitute. This course has no DORA grading, so there is no dora_tests notebook; the dora/
folder only holds account_setup, to keep the same layout and tooling as the other badges.
"""
import base64, html, json, os, re, shutil, uuid, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE = os.path.join(ROOT, "badges", "snowflake-x-genai-llm-functions")
ASSETS = os.path.join(COURSE, "assets")
OUT = os.path.join(ROOT, "notebooks", "sxga2_llm_functions")

ADMIN_ROLE, SYSADMIN_ROLE, WAREHOUSE = "SXGA2_LLM_ADMIN", "SXGA2_LLM_ROLE", "SXGA2_LLM_WH"
DOWNLOADS = "@UTIL_DB.PUBLIC.SXGA2_LLM_DOWNLOADS"
SECRET = "UTIL_DB.PUBLIC.SXGA2_API_NINJAS_KEY"
SETUP_NB = "dora/account_setup"

# Rise truncates asset names; these are the names the course gives in its text
PDF_NAMES = {
    "99 Red Balloons by Nena.pdf": "99 Red Balloons by Nena.pdf",
    "Beyond the Sea by Bobby Da.pdf": "Beyond the Sea by Bobby Darin.pdf",
    "Cutie Pie by One Way.pdf": "Cutie Pie by One Way.pdf",
    "Flashdance... What a Feeli.pdf": "Flashdance... What a Feeling by Irene Cara.pdf",
    "Fortnight by Taylor Swift.pdf": "Fortnight by Taylor Swift.pdf",
    "Gloria by Laura Branigan.pdf": "Gloria by Laura Branigan.pdf",
    "Mary Had A Little Lamb by.pdf": "Mary Had A Little Lamb by Storybooksong.pdf",
    "Ribbon in the Sky by Stevi.pdf": "Ribbon in the Sky by Stevie Wonder.pdf",
    "September by Earth, Wind &.pdf": "September by Earth, Wind & Fire.pdf",
    "The Girl From Ipanema by A.pdf": "The Girl From Ipanema by Amy Winehouse.pdf",
}
TRAINING = ["Mary Had A Little Lamb by Storybooksong.pdf", "Beyond the Sea by Bobby Darin.pdf", "September by Earth, Wind & Fire.pdf",
            "Gloria by Laura Branigan.pdf", "Fortnight by Taylor Swift.pdf", "Cutie Pie by One Way.pdf"]
LESSON5 = ["The Girl From Ipanema by Amy Winehouse.pdf", "99 Red Balloons by Nena.pdf", "Ribbon in the Sky by Stevie Wonder.pdf",
           "Flashdance... What a Feeling by Irene Cara.pdf"]


def zip_pdfs():
    out = {}
    z = zipfile.ZipFile(os.path.join(ASSETS, "More_songs.zip"))
    for i in z.infolist():
        if i.is_dir() or "__MACOSX" in i.filename:
            continue
        n = i.filename if i.flag_bits & 0x800 else i.filename.encode("cp437").decode("utf-8")
        out[os.path.basename(n)] = z.read(i)
    return out


AUTOMATED = sorted(zip_pdfs())

# the 7 value/question pairs the course sets up in the Document AI UI (LLMM_141-149)
QUESTIONS = [("song_title", "What is the name of this song?"), ("performing_artist", "Who performed this version of the song?"),
             ("lyrics", "What are the lyrics to this song?"), ("authors", "Who wrote this song?"),
             ("lyrics_copyright_holders", "Who holds the copyright to the lyrics?"),
             ("lyric_licensor_provider", "Who licensed and provided the lyrics?"), ("source", "Who provided the pdf document?")]
RESPONSE_FORMAT = "{" + ",".join(f"'{k}':'{q}'" for k, q in QUESTIONS) + "}"


# ---------------------------------------------------------------- course code
_raw = open(os.path.join(COURSE, "runtime-data.js")).read()
_course = json.loads(base64.b64decode(re.search(r'__jsonp\("runtime-data.js","(.*)"\)', _raw, re.S).group(1)))["course"]
CODE = {}
for _l in _course["lessons"]:
    _codes = [html.unescape(x.get("code") or "").replace("\r\n", "\n").strip("\n")
              for it in _l.get("items") or [] if it.get("type") == "multimedia" and it.get("variant") == "code"
              for x in it["items"]]
    if _codes:
        CODE[re.sub(r"<[^>]+>", "", _l["title"]).strip()] = _codes


def code(page, i=0):
    hits = [k for k in CODE if page in k]
    assert len(hits) == 1, (page, hits)
    return CODE[hits[0]][i]


def isolate(sql):
    sql = re.sub(r"\bACCOUNTADMIN\b", "{{ADMIN_ROLE}}", sql, flags=re.I)
    sql = re.sub(r"\bSYSADMIN\b", "{{SYSADMIN_ROLE}}", sql, flags=re.I)
    return re.sub(r"\bCOMPUTE_WH\b", "{{WAREHOUSE}}", sql, flags=re.I)


def stmts(text):
    """Split a course block into statements (the blocks used here have no ';' inside strings)."""
    return [s.strip() + ";" for s in text.split(";") if s.strip()]


def protected(sql_text):
    """Run course code as given, reporting instead of stopping if it errors (nested single-quoted so $$ bodies work)."""
    body = ("begin\n  execute immediate '" + sql_text.strip().rstrip(";").replace("'", "''") +
            "';\n  return 'ran without error';\nexception when other then\n  return 'Error (as run today): ' || sqlerrm;\nend;")
    return "execute immediate '" + body.replace("'", "''") + "';"


def _id():
    return uuid.uuid4().hex[:8]


def md(text):
    return {"cell_type": "markdown", "id": _id(), "metadata": {}, "source": text.strip("\n")}


def sql(name, text):
    return {"cell_type": "code", "id": _id(), "execution_count": None, "outputs": [],
            "metadata": {"language": "sql", "name": name}, "source": f"%%sql -r {name}\n" + text.strip("\n")}


def py(name, text):
    return {"cell_type": "code", "id": _id(), "execution_count": None, "outputs": [],
            "metadata": {"language": "python", "name": name}, "source": text.strip("\n")}


def course(text):
    return md("> **Course:** " + text.strip().replace("\n", "\n> "))


def note(text):
    return md("> ⚠️ **Audit note:** " + text.strip().replace("\n", "\n> "))


def update(text):
    return md("> 🛠️ **Course update needed:** " + text.strip().replace("\n", "\n> "))


def page(title):
    return md(f"## Page: {title}")


def story(*titles):
    return md("Story / reading / knowledge-check pages, nothing to run: " + "; ".join(titles) + ".")


PREAMBLE_VARS = f"""# Isolation mapping (set once per notebook; SQL cells use these via {{{{...}}}})
ADMIN_ROLE    = "{ADMIN_ROLE}"   # stands in for the course's ACCOUNTADMIN
SYSADMIN_ROLE = "{SYSADMIN_ROLE}"    # stands in for the course's SYSADMIN
WAREHOUSE     = "{WAREHOUSE}"      # stands in for the course's COMPUTE_WH


def pdf(result):
    \"\"\"A SQL cell's result as pandas (runtime 2.6+ returns a Snowpark DataFrame).\"\"\"
    return result.to_pandas() if hasattr(result, "to_pandas") else result"""

SUB_NOTE = ("Substitute cells use the current `AI_*` functions. The legacy `SNOWFLAKE.CORTEX.TRANSLATE`, `SENTIMENT` and `SUMMARIZE` "
            "are blocked on new accounts (verified 2026-11-14: \"New accounts are blocked from using legacy SNOWFLAKE.CORTEX functions\").")


def preamble(title, purpose, schema=None):
    ctx = "use role {{SYSADMIN_ROLE}};\nuse secondary roles none;\nuse warehouse {{WAREHOUSE}};\n"
    ctx += f"use schema {schema};\n" if schema else ""
    return [
        md(f"# Snowflake x GenAI: LLM Functions: {title}\n\n{purpose}\n\n"
           "**How to read this notebook**\n"
           "- Each `## Page:` heading is one page of the Rise lesson, in course order.\n"
           "- `> Course:` cells quote what the learner is told to do (text or screenshot steps).\n"
           "- Code cells run that task. Course code is verbatim except role/warehouse names, swapped for "
           f"`{ADMIN_ROLE}` (ACCOUNTADMIN), `{SYSADMIN_ROLE}` (SYSADMIN) and `{WAREHOUSE}` (COMPUTE_WH).\n"
           "- Course code that no longer works runs **as written** and reports its error; a **Substitute** cell with current functions follows it.\n"
           "- **SQL equivalent** replaces a UI-only step; **From screenshot** marks code the course shows only as an image; "
           "**Derived solution** marks challenge answers the course does not give.\n"
           "- 🛠️ **Course update needed** marks what has to change in the course itself.\n"
           f"- Files the course has learners download are on `{DOWNLOADS}`, standing in for the learner's Downloads folder.\n\n"
           f"Prerequisite: run `{SETUP_NB}.ipynb` once."),
        py("isolation_vars", PREAMBLE_VARS),
        sql("session_context", ctx + "select current_role(), current_warehouse(), current_database(), current_schema();"),
    ]


SIX_Q = RESPONSE_FORMAT.replace("'lyrics':'What are the lyrics to this song?',", "")
LYRICS_FN = ("create or replace function doc_ai_db.doc_ai_schema.lyrics_extractor(f file) returns object as\n$$ (select object_construct_keep_null('error', e:error, 'response', object_insert(e:response, 'lyrics', ai_parse_document(f, {'mode':'OCR'}):content::varchar))\n"
             f"    from (select ai_extract(file => f, responseFormat => {SIX_Q}) as e)) $$;")


def extract_cell(name, stage, path_expr, extra=""):
    return sql(name, f"{extra}select to_varchar(ai_extract(file => to_file('{stage}', {path_expr}),\n  responseFormat => {RESPONSE_FORMAT})) as extracted;")


NB = {}

# ---------------------------------------------------------------- setup
ALL_PDFS = sorted(set(PDF_NAMES.values()) | set(AUTOMATED))
NB[SETUP_NB] = [
    md("# SXGA2: Setup (run once, as ACCOUNTADMIN)\n\nCreates the isolated environment the lesson notebooks run in:\n\n"
       "| Course object | Isolated stand-in | Notes |\n|---|---|---|\n"
       f"| ACCOUNTADMIN role | `{ADMIN_ROLE}` | holds the account privileges the course uses as ACCOUNTADMIN |\n"
       f"| SYSADMIN role | `{SYSADMIN_ROLE}` | granted to `{ADMIN_ROLE}`, mirroring SYSADMIN under ACCOUNTADMIN |\n"
       f"| COMPUTE_WH | `{WAREHOUSE}` | X-Small, auto-suspend, owned by `{SYSADMIN_ROLE}` |\n"
       "| UTIL_DB | `UTIL_DB` | shared across badges; owned by SYSADMIN |\n"
       f"| learner's Downloads folder | `{DOWNLOADS}` | holds the lyric PDFs the course has learners download |\n"
       f"| learner's API Ninjas key | `{SECRET}` | a Snowflake secret. The key is never written into a notebook. |\n\n"
       "Create the secret once, outside these notebooks, with your own key from api-ninjas.com:\n\n"
       f"```sql\nuse role accountadmin;\ncreate or replace secret {SECRET} type = generic_string secret_string = '<your API Ninjas key>';\n```\n\n"
       "Course objects (SXGA2, DOC_AI_ROLE, DOC_AI_WH, DOC_AI_DB, the API integration, ...) keep the course's exact names and are created in the lessons."),
    py("isolation_vars", PREAMBLE_VARS),
    md("## Check for name collisions\nCourse object names are account-wide."),
    sql("existing_course_objects", "use role accountadmin;\nshow databases like 'SXGA2';\nshow databases like 'DOC_AI_DB';\nshow roles like 'DOC_AI_ROLE';\n"
        "show warehouses like 'DOC_AI_WH';\nshow integrations like 'API_NINJAS_ACCESS_INTEGRATION';"),
    md("## Roles and grants"),
    sql("create_roles", """use role accountadmin;
create role if not exists {{ADMIN_ROLE}} comment = 'SXGA2 stand-in for ACCOUNTADMIN';
create role if not exists {{SYSADMIN_ROLE}} comment = 'SXGA2 stand-in for SYSADMIN';
grant role {{SYSADMIN_ROLE}} to role {{ADMIN_ROLE}};
grant role {{ADMIN_ROLE}} to role sysadmin;
set badge_user = current_user();
grant role {{ADMIN_ROLE}} to user identifier($badge_user);
grant role {{SYSADMIN_ROLE}} to user identifier($badge_user);
-- SYSADMIN creates the SXGA2 database (Lesson 3)
grant create database on account to role {{SYSADMIN_ROLE}};
-- the course's ACCOUNTADMIN steps: external access integration (Lesson 3)
grant create integration on account to role {{ADMIN_ROLE}};
-- AI functions
grant database role snowflake.cortex_user to role {{SYSADMIN_ROLE}};
grant database role snowflake.cortex_user to role {{ADMIN_ROLE}};
grant database role snowflake.ai_functions_user to role {{SYSADMIN_ROLE}};
grant database role snowflake.ai_functions_user to role {{ADMIN_ROLE}};
grant imported privileges on database snowflake to role {{ADMIN_ROLE}};"""),
    md("## Warehouse (stands in for COMPUTE_WH)"),
    sql("create_warehouse", """use role accountadmin;
create warehouse if not exists {{WAREHOUSE}}
  warehouse_size = xsmall auto_suspend = 60 auto_resume = true initially_suspended = true
  comment = 'SXGA2 stand-in for COMPUTE_WH';
grant ownership on warehouse {{WAREHOUSE}} to role {{SYSADMIN_ROLE}} copy current grants;"""),
    md("## UTIL_DB (shared across badges) and the API key secret"),
    sql("util_db_grants", f"""use role accountadmin;
create database if not exists UTIL_DB comment = 'Shared utility database for badge course audits (DORA grader, course stages)';
grant ownership on database UTIL_DB to role sysadmin copy current grants;
grant ownership on schema UTIL_DB.PUBLIC to role sysadmin copy current grants;
grant usage on database UTIL_DB to role {{{{ADMIN_ROLE}}}};
grant usage on database UTIL_DB to role {{{{SYSADMIN_ROLE}}}};
grant usage, create stage, create workspace on schema UTIL_DB.PUBLIC to role {{{{ADMIN_ROLE}}}};
grant usage on schema UTIL_DB.PUBLIC to role {{{{SYSADMIN_ROLE}}}};
-- the function in Lesson 3 reads the API key from this secret, so its owner role needs usage
grant read on secret {SECRET} to role {{{{ADMIN_ROLE}}}};
grant read on secret {SECRET} to role {{{{SYSADMIN_ROLE}}}};
grant usage on secret {SECRET} to role {{{{ADMIN_ROLE}}}};
grant usage on secret {SECRET} to role {{{{SYSADMIN_ROLE}}}};"""),
    md("## Course data files (the learner's Downloads folder)\nThe lyric PDFs are in `data/` beside these notebooks; upload them once:\n\n"
       f"```\nsnow sql -q \"use role {ADMIN_ROLE}; put 'file://<path>/data/*' {DOWNLOADS} auto_compress=false overwrite=true\"\n```"),
    sql("create_downloads_stage", f"""use role {{{{ADMIN_ROLE}}}};
create stage if not exists {DOWNLOADS[1:]}
  comment = 'SXGA2: stands in for the learner''s local Downloads folder'
  directory = (enable = true)
  encryption = (type = 'SNOWFLAKE_SSE');
grant read on stage {DOWNLOADS[1:]} to role {{{{SYSADMIN_ROLE}}}};
grant read on stage {DOWNLOADS[1:]} to role {{{{ADMIN_ROLE}}}};
alter stage {DOWNLOADS[1:]} refresh;
list {DOWNLOADS};"""),
    py("downloads_check", f"""expected = {ALL_PDFS!r}
found = sorted(n.split('/')[-1] for n in pdf(create_downloads_stage)['name'])
print('Missing course files:', sorted(set(expected) - set(found)) or 'none')"""),
    md("## Teardown (commented out)"),
    sql("teardown", """-- use role accountadmin;
-- drop database if exists SXGA2;
-- drop database if exists DOC_AI_DB;
-- drop warehouse if exists DOC_AI_WH;
-- drop role if exists DOC_AI_ROLE;
-- drop integration if exists API_NINJAS_ACCESS_INTEGRATION;
-- drop stage if exists UTIL_DB.PUBLIC.SXGA2_LLM_DOWNLOADS;
-- drop warehouse if exists {{WAREHOUSE}};
-- drop role if exists {{SYSADMIN_ROLE}};
-- drop role if exists {{ADMIN_ROLE}};
select 'teardown is commented out' as status;"""),
]

# ---------------------------------------------------------------- lesson 1
NB["lesson_01_getting_started_and_functions"] = preamble("Getting Started + Lesson 1: The CORTEX LLM Functions", "Prerequisites checklist and locating the functions.") + [
    page("Getting Started!"),
    course("Confirmation checklist: Snowflake experience; read SXGA Module 1; free trial account (AWS US West (Oregon) strongly recommended); account-level resource monitor; payment method added to enable AI/Cortex functions."),
    sql("account_details", "select current_region() as region, current_account() as locator, current_user() as user_name;"),
    sql("resource_monitors", "use role {{ADMIN_ROLE}};\nshow resource monitors;"),
    update("The checklist says AI features are off on trial accounts until a payment method is on file. This account is paid, so that could not be verified. The checklist link `uni-fod-sxga` also 404s (see the existing audit L0-1)."),
    page("Haikus Were Just the Beginning"), md("Reading only."),
    update("\"Snowflake's embedded AI Tools like LLM Functions and Document AI tool.\" Document AI is decommissioned and the functions are now called Cortex AI Functions (AI_*)."),
    page("Locating the LLM Functions"),
    course("🧪 LAB: Navigate to the TRANSLATE() Function (translate_1.png, translate_2.png): Snowsight Catalog → SNOWFLAKE → CORTEX schema → Functions. Then answer: *In addition to the AI_TRANSLATE() Function listed in the SNOWFLAKE.CORTEX schema, what other function names do you see included?*"),
    sql("show_cortex_functions", "-- SQL equivalent of browsing SNOWFLAKE.CORTEX in the catalog\nshow functions like '%TRANSLATE%' in schema snowflake.cortex;"),
    sql("show_cortex_ai_functions", "show functions like 'AI_%' in schema snowflake.cortex;"),
    update("The lab screenshots highlight the legacy `SNOWFLAKE.CORTEX.TRANSLATE`; recapture them on `AI_TRANSLATE`. The quiz keys `AI_EMBED_TEXT_768`, which does not exist (this account has `AI_EMBED_768`)."),
]

# ---------------------------------------------------------------- lesson 2
NB["lesson_02_translate"] = preamble("Lesson 2: The TRANSLATE() Function", "AI_TRANSLATE, reverse translation, and the legacy TRANSLATE functions.") + [
    page("Calling the Translate Function"),
    course("🧪 LAB: Call the Translate Function. Paste the code snippet into a worksheet and run it."),
    sql("translate_hello", code("Calling the Translate Function")),
    course("🎯 CHALLENGE LAB: Reverse Translation. Take the value we just received and translate it back to English (LLMM_080)."),
    sql("reverse_translate", "-- Derived solution\nselect ai_translate('こんにちは', 'ja', 'en');"),
    note("LLMM_080 shows `snowflake.cortex.translate(...)` (the legacy function). The course's own code on this page already uses `ai_translate`; the page is half-migrated."),
    page("Special TRANSLATE() Considerations"),
    course("🧪 LAB: Set the Worksheet Context (LLMM_085, 086): choose database SNOWFLAKE and schema CORTEX. Then run the three forms (fully qualified, partially qualified, not qualified). Only the first two call the Cortex function; the bare `translate(...)` is the plain string function that replaces characters."),
    sql("set_cortex_context", "-- SQL equivalent of the Choose database drop-down\nuse schema snowflake.cortex;"),
    note(SUB_NOTE),
    sql("translate_qualified_forms", protected("select\n    snowflake.cortex.translate('Goodbye!', 'en', 'fr')\n    , cortex.translate('Goodbye!', 'en', 'fr')\n    , translate('Goodbye!', 'en', 'fr');")),
    sql("translate_bare_string_function", "-- LLMM_086 third column: the bare name resolves to the global string function TRANSLATE (character replacement), not an AI function\nselect translate('Goodbye!', 'en', 'fr') as not_qualified;"),
    sql("translate_substitute_forms", "-- Substitute: the current function. `ai_translate` is the same from any schema, so the \"will not return\" trap disappears\nselect ai_translate('Goodbye!', 'en', 'fr') as fully_qualified_equivalent,\n       snowflake.cortex.ai_translate('Goodbye!', 'en', 'fr') as qualified;"),
    update("The whole 'bare TRANSLATE() is a different function' lesson only applies to the legacy name. With `AI_TRANSLATE` there is nothing to confuse; reword or drop the page and its quiz."),
    page("Reverse Translation to Check Quality"),
    course("🧪 LAB: Create a Variable and Test It (LLMM_086): `set my_text = 'My favorite color is blue.';` then `select $my_text;`."),
    sql("set_my_text", "-- From screenshot LLMM_086\nset my_text = 'My favorite color is blue.';\n\nselect $my_text;"),
    course("🧪 LAB: Call the Translate Function Using the Variable (the course's code, which uses `cortex.translate`)."),
    sql("reverse_translation_as_given", protected(code("Reverse Translation to Check Quality"))),
    sql("reverse_translation_substitute", "-- Substitute: the same query with ai_translate\nselect $my_text as OG_ENGLISH\n    , ai_translate($my_text, 'en', 'fr') as EN_2_FR\n    , ai_translate(EN_2_FR, 'fr', 'en') as EN_2_FR_2_EN\n    , OG_ENGLISH = EN_2_FR_2_EN as Reverse_Translation_Success;"),
    sql("reverse_translation_quote", "-- Derived: the course suggests trying quotes; most fail the exact-match column but keep their meaning\nset my_text = 'The best and most beautiful things in the world cannot be seen or even touched, they must be felt with the heart.';\n"
        "select $my_text as OG_ENGLISH\n    , ai_translate($my_text, 'en', 'fr') as EN_2_FR\n    , ai_translate(EN_2_FR, 'fr', 'en') as EN_2_FR_2_EN\n    , OG_ENGLISH = EN_2_FR_2_EN as Reverse_Translation_Success;"),
    page("Checking the Quality of GenAI"), md("Reading only (GenAI animation commentary)."),
    update("The animation commentary (Bing Image Creator, aitubo.com models) is dated and refers to a 'last month' state of the art."),
]

# ---------------------------------------------------------------- lesson 3
FUNCTION_V1 = """create or replace function get_api_data()
returns varchar
language python
runtime_version=3.9
handler = 'get_the_data'
packages = ('requests')
as
$$
import requests

api_url = 'https://api.api-ninjas.com/v1/quotes'
api_key = 'YOUR API KEY'

response = requests.get(api_url, headers={'X-Api-Key': api_key})
if response.status_code == requests.codes.ok:
    return response.text
else:
    return "Error:", response.status_code, response.text
$$;"""
FUNCTION_V2 = """create or replace function get_api_data()
returns varchar
language python
runtime_version=3.9
handler = 'get_the_data'
packages = ('requests')
as
$$
import requests

api_url = 'https://api.api-ninjas.com/v1/quotes'
api_key = 'YOUR API KEY'

def get_the_data():
    response = requests.get(api_url, headers={'X-Api-Key': api_key})
    if response.status_code == requests.codes.ok:
        return response.text
    else:
        return response.status_code
$$;"""
FUNCTION_V3 = FUNCTION_V2.replace("packages = ('requests')\nas", "packages = ('requests')\nexternal_access_integrations = (api_ninjas_access_integration)\nas")
FUNCTION_SUB = """create or replace function get_api_data()
returns varchar
language python
runtime_version=3.12
handler = 'get_the_data'
packages = ('requests')
external_access_integrations = (api_ninjas_access_integration)
secrets = ('api_key' = UTIL_DB.PUBLIC.SXGA2_API_NINJAS_KEY)
as
$$
import requests
import _snowflake

api_url = 'https://api.api-ninjas.com/v1/quotes'

def get_the_data():
    api_key = _snowflake.get_generic_secret_string('api_key')
    response = requests.get(api_url, headers={'X-Api-Key': api_key})
    if response.status_code == requests.codes.ok:
        return response.text
    else:
        return response.status_code
$$;"""

NB["lesson_03_sentiment"] = preamble("Lesson 3: The SENTIMENT() Function", "SENTIMENT, the API Ninjas quotes function, RAW_QUOTES.") + [
    page("It's a Whole Mood"),
    course("🧪 LAB: Plug a Mood Into the SENTIMENT() Function; try the other moods (Giddy, Reflective, Pensive, Agitated, Blithe, Rhapsodic, Dejected, Doleful, Lacrymose). Troubleshooting: set the worksheet context to SNOWFLAKE.CORTEX or fully qualify the name."),
    note(SUB_NOTE),
    sql("sentiment_as_given", protected(code("It's a Whole Mood", 0))),
    sql("sentiment_qualified_as_given", protected(code("It's a Whole Mood", 1))),
    sql("sentiment_substitute", "-- Substitute: AI_SENTIMENT returns an OBJECT with a label per category, not a number from -1 to 1\nselect ai_sentiment('disconsolate') as result,\n       ai_sentiment('disconsolate'):categories[0]:sentiment::text as label;"),
    sql("sentiment_moods_substitute", "select mood, ai_sentiment(mood):categories[0]:sentiment::text as label\nfrom (select column1 as mood from values ('Giddy'),('Reflective'),('Pensive'),('Agitated'),('Blithe'),('Rhapsodic'),('Dejected'),('Doleful'),('Lacrymose'));"),
    update("`AI_SENTIMENT` is not a drop-in replacement: it returns labels (positive / negative / neutral / mixed / unknown), not a score. The page premise (\"ranks it between -1 and 1\"), the lab prediction exercise, LLMM_090 and everything later that uses a score must be rewritten."),
    page("Cyborg Bear Animation - Round 2"), md("Reading and quiz only."),
    page("Applying Sentiment to Quotes"),
    course("🧪 LAB: Sign Up for a Free Account on API Ninjas (LLMM_091-095): verify your email, log in to the dashboard, copy the API key (\"the API Key is your password for using the API\")."),
    sql("secret_exists", "-- Not a course cell: confirms the API key secret from the setup notebook exists (the key itself is never shown)\nshow secrets like 'SXGA2_API_NINJAS_KEY' in schema UTIL_DB.PUBLIC;"),
    page("Preparing Code to Call the API"),
    course("🧪 LAB: Reading the Documentation (api-ninjas.com quotes API: optional parameter `category`; the key goes in the `X-Api-Key` header). 🧪 LAB: paste the sample Python into a worksheet, create a variable for the API key, convert PRINT() to RETURN, add the function header and closing `$$`s (LLMM_098, 100, 101)."),
    page("Finessing Our Function that Calls the API"),
    course("🎯 CHALLENGE LAB: Create an SXGA2 Infrastructure: give SYSADMIN USAGE on COMPUTE_WH; set your default role to SYSADMIN; set your worksheet role to SYSADMIN; create database SXGA2; drop the PUBLIC schema; create schema NINJAS; double-check both are owned by SYSADMIN."),
    sql("create_sxga2", "-- Derived solution. The stand-in warehouse is already owned by the SYSADMIN stand-in, and default role/user settings are not changed here.\nuse role {{SYSADMIN_ROLE}};\n"
        "create database SXGA2;\ndrop schema SXGA2.PUBLIC;\ncreate schema SXGA2.NINJAS;\nuse warehouse {{WAREHOUSE}};\nuse schema SXGA2.NINJAS;"),
    sql("check_sxga2_owner", "show databases like 'SXGA2';\nshow schemas in database SXGA2;"),
    course("🧪 LAB: Try to Create the Function (LLMM_101, 102): the first version fails with `'return' outside function`."),
    note("The course's functions use `runtime_version=3.9`, which no longer exists (\"Python runtime version 3.9 is decommissioned\"). They run as written below and report that error; the **Substitute** cell uses 3.12."),
    sql("function_attempt_1", protected(FUNCTION_V1)),
    course("🧪 LAB: Try to Create the Function, Again: add a line and indent the lines underneath to create the HANDLER (LLMM_103), then try to call it (LLMM_104)."),
    sql("function_attempt_2", protected(FUNCTION_V2)),
    sql("call_function_attempt_2", protected("select get_api_data();")),
    course("🧪 LAB: Create a Network Rule (LLMM_106, 107): name **api_ninjas_network_access** in SXGA2.NINJAS, comment *this makes it okay for us to send messages out to the api*, Type Host Port, Mode Egress, identifier **api.api-ninjas.com**."),
    sql("create_network_rule", "-- SQL equivalent of the Create Network Rule dialog (LLMM_106)\nuse role {{ADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\nuse schema SXGA2.NINJAS;\n"
        "create or replace network rule api_ninjas_network_access\n  mode = egress\n  type = host_port\n  value_list = ('api.api-ninjas.com')\n  comment = 'this makes it okay for us to send messages out to the api';"),
    course("🧪 LAB: Put the Rule into an Integration. *If you are using a trial account you MUST enter a billing credit card.*"),
    sql("create_integration", "use schema SXGA2.NINJAS;\n" + isolate(code("Finessing Our Function", 0)).replace("use role {{ADMIN_ROLE}};\n\n", "use role {{ADMIN_ROLE}};\n")),
    sql("grant_integration", isolate(code("Finessing Our Function", 1))),
    update("The note that a credit card is required for external access on a trial is wrong according to the existing audit: trial accounts cannot use external network access at all, with or without a card."),
    course("🧪 LAB: Add the Integration to the Function (then test it once again) (LLMM_109: `external_access_integrations = (api_ninjas_access_integration)`)."),
    sql("function_with_integration", "use role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\nuse schema SXGA2.NINJAS;\n" + FUNCTION_V3.replace("create or replace function get_api_data()", "create or replace function get_api_data()") if False else protected(FUNCTION_V3)),
    note("**Secret instead of a typed key.** The course puts the key in the function text (`api_key = 'YOUR API KEY'`) and says later that production code should move it into a SECRET. The substitute below does that from the start so the key never appears in a notebook or the public repo: "
         "the integration is allowed to use the secret, and the function reads it with `_snowflake.get_generic_secret_string`."),
    sql("allow_secret_on_integration", "-- Substitute step: let the integration use the secret\nuse role {{ADMIN_ROLE}};\nalter external access integration api_ninjas_access_integration set allowed_authentication_secrets = (UTIL_DB.PUBLIC.SXGA2_API_NINJAS_KEY);\n"
        "grant usage on integration api_ninjas_access_integration to role {{SYSADMIN_ROLE}};"),
    sql("function_substitute", "use role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\nuse schema SXGA2.NINJAS;\n-- Substitute: Python 3.12 and the key from a secret\n" + FUNCTION_SUB),
    sql("call_function", "select get_api_data();"),
    page("Improving & Using Our Request Function"),
    course("🎯 CHALLENGE LAB: Create a Table to Hold the JSON Quotes: RAW_QUOTES with one column JSON of type VARIANT, owned by SYSADMIN."),
    sql("create_raw_quotes", "-- Derived solution\ncreate table raw_quotes (json variant);"),
    course("🧪 LAB: Testing Code Until We Get Results We Can Use. Run each statement separately."),
    *[sql(n, s) if n != "quotes_insert_raw" else sql(n, protected(s)) for n, s in zip(
        ["quotes_insert_raw", "quotes_insert_parsed", "quotes_select_1", "quotes_insert_replaced", "quotes_select_2", "quotes_parse"], stmts(code("Improving & Using Our Request Function", 0)))],
    course("🎯 CHALLENGE LAB: Generate at Least 10 Rows of Data. Make sure the rows parse properly; get rid of any rows that won't work (or edit them)."),
    sql("generate_quotes", "-- Derived solution: call the API nine more times with the bracket-free insert (the API returns a random quote each call)\nexecute immediate $$\nbegin\n  for i in 1 to 9 do\n"
        "    insert into raw_quotes select parse_json(replace(replace(get_api_data(),'['),']'));\n  end for;\n  return 'inserted';\nend;\n$$;"),
    sql("remove_unparseable_rows", "-- Derived solution: the rows from the first two test inserts still have the [ ] array around the quote\ndelete from raw_quotes where is_array(json) or json:quote is null;\nselect count(*) as usable_rows from raw_quotes;"),
    sql("quotes_parsed_check", "select json:author::text as author, json:quote::text as quote, json:category::text as category from raw_quotes;"),
    course("🧪 LAB: Use TRANSLATE() and SENTIMENT() on Your Quotes Table (LLMM_114)."),
    sql("quotes_cortex_as_given", protected(code("Improving & Using Our Request Function", 1))),
    sql("quotes_cortex_substitute", "-- Substitute: ai_sentiment (label) and ai_translate\nselect json:author::text as author\n     , ai_sentiment(json:quote::text):categories[0]:sentiment::text as quote_sentiment\n"
        "     , ai_translate(json:quote::text,'en', 'sv') as quote_swedish\n     , json:quote::text as original_quote\n     , json:category::text as category\nfrom raw_quotes;"),
    note("Another Improvement? The course defers moving the API key into a SECRET; this notebook already does it (see above)."),
]

# ---------------------------------------------------------------- lesson 4
DOC_CTX = "use role doc_ai_role;\nuse warehouse doc_ai_wh;\nuse schema doc_ai_db.doc_ai_schema;\n"
TRAIN_LIST = ", ".join(f"'{n}'" for n in TRAINING)


def copy_files(stage, names):
    return f"copy files into @{stage}\nfrom {DOWNLOADS}\nfiles = (" + ", ".join(f"'{n}'" for n in names) + ");"


NB["lesson_04_ml_model_on_an_llm"] = preamble("Lesson 4: A Machine Learning Model Based on an LLM", "The Document AI setup, and AI_EXTRACT as its replacement.") + [
    page("Gathering Data for the SUMMARIZE() Function"),
    update("**Document AI is decommissioned** (BCR-2156, 2026-03-16). `CREATE SNOWFLAKE.ML.DOCUMENT_INTELLIGENCE` no longer parses in this account, there is no Document AI page in Snowsight, and `<model>!PREDICT` is gone. The replacement is `AI_EXTRACT`: no model is built or trained, and the questions are passed in `responseFormat`. "
           "Lessons 4-6 are rebuilt below around AI_EXTRACT on the same lyric PDFs, with the same seven questions."),
    course("The Doc AI infrastructure: a role, a warehouse, a database and a schema, each created with the scripts below, in order."),
    note("These are account-level steps, so they run as the real ACCOUNTADMIN. Nothing in the AI_EXTRACT flow needs them (AI functions are available to PUBLIC); they are kept because the later course steps and screenshots refer to DOC_AI_ROLE, DOC_AI_WH and DOC_AI_DB."),
    sql("create_doc_ai_role", "use role accountadmin;\ncreate role doc_ai_role;\n\ngrant database role SNOWFLAKE.DOCUMENT_INTELLIGENCE_CREATOR to role doc_ai_role;\n\nset badge_user = current_user();\ngrant role doc_ai_role to user identifier($badge_user);"),
    sql("confirm_doc_ai_role", "-- LLMM_116, 117: confirm the role and that it's assigned to you\nshow roles like 'DOC_AI_ROLE';\nshow grants to user identifier($badge_user);"),
    sql("create_doc_ai_wh", code("Gathering Data for the SUMMARIZE() Function", 1).replace("grant USAGE", "use role accountadmin;\ngrant USAGE") if False else "use role accountadmin;\n" + code("Gathering Data for the SUMMARIZE() Function", 1)),
    sql("confirm_doc_ai_wh", "-- LLMM_119, 120\nshow warehouses like 'DOC_AI_WH';\nshow grants on warehouse doc_ai_wh;"),
    sql("create_doc_ai_db", "use role accountadmin;\n" + code("Gathering Data for the SUMMARIZE() Function", 2)),
    sql("confirm_doc_ai_db", "-- LLMM_122\nshow databases like 'DOC_AI_DB';\nshow grants on database doc_ai_db;"),
    course("🧪 LAB: Switch Your Role to DOC_AI_ROLE Before Moving Forward! Then create the DOC_AI_SCHEMA and grant privileges (the role must own the schema)."),
    sql("create_doc_ai_schema", "use role doc_ai_role;\nuse warehouse doc_ai_wh;\n" + "\n\n".join(stmts(code("Gathering Data for the SUMMARIZE() Function", 3))[:3])),
    note("The course's last grant (`CREATE SNOWFLAKE.ML.DOCUMENT_INTELLIGENCE on SCHEMA`) is run on its own below; it reports its result because that privilege belongs to the retired feature."),
    sql("grant_create_document_intelligence", protected("use role doc_ai_role;\n" + stmts(code("Gathering Data for the SUMMARIZE() Function", 3))[3]) if False else
        protected(stmts(code("Gathering Data for the SUMMARIZE() Function", 3))[3])),
    page("Your First Machine Learning Model?"),
    course("🥋 LAB: Navigate to the Document AI Homepage: AI & ML → Document AI, with DOC_AI_ROLE and DOC_AI_WH, then build a new model (lyrics_1.png, lyrics_2.png)."),
    update("The Document AI homepage and **Build** button no longer exist. There is no model to build. Retire both images; the section title is also wrong (\"A Machine Learning Model Based on an LLM\")."),
    page("Loading a PDF Lyric Sheet"),
    course("🧪 LAB: Upload a Document for Training (Mary Had A Little Lamb by Storybooksong.pdf; LLMM_136-139)."),
    sql("create_training_stage", "-- Substitute for the model-build upload: the PDFs go on a stage instead. The course's stage LYRICS_PDFS is created in Lesson 5, so the training PDFs use their own stage.\n"
        + DOC_CTX + "create stage training_pdfs\n  directory = (enable = true)\n  encryption = (type = 'SNOWFLAKE_SSE');"),
    sql("load_training_pdfs", "-- Isolation grants (not a course step): the Downloads stand-in stage is in UTIL_DB, which DOC_AI_ROLE cannot otherwise see. Real ACCOUNTADMIN.\nuse role accountadmin;\n"
        "grant usage on database UTIL_DB to role doc_ai_role;\ngrant usage on schema UTIL_DB.PUBLIC to role doc_ai_role;\ngrant read on stage " + DOWNLOADS[1:] + " to role doc_ai_role;\n"
        "-- SQL equivalent of uploading the six training PDFs from the Downloads folder\n" + DOC_CTX + copy_files("doc_ai_db.doc_ai_schema.training_pdfs", TRAINING)
        + "\nalter stage training_pdfs refresh;\nlist @training_pdfs;"),
    page("Choosing Values & Asking the LLM Questions"),
    course("📓 Define VALUES as future table columns, each with a question: song_title *What is the name of this song?*; performing_artist *Who performed this version of the song?*; lyrics *What are the lyrics to this song?*; authors *Who wrote this song?*; "
           "lyrics_copyright_holders *Who holds the copyright to the lyrics?*; lyric_licensor_provider *Who licensed and provided the lyrics?*; source *Who provided the pdf document?* "
           "The LLM gives an answer and a confidence score; approving it sets the score to 1.00 and \"the model will learn from the feedback loop\" (LLMM_141-150)."),
    note("`AI_EXTRACT` returns the answers only, no confidence score, and nothing is learned from approvals. Six of the seven questions become `responseFormat` keys."),
    note("**The `lyrics` question cannot be asked with AI_EXTRACT.** Verified 2026-11-14: for any copyrighted lyric sheet (every PDF except Mary Had A Little Lamb) `AI_EXTRACT` answers \"AI_EXTRACT failed: the model refused to answer\" and returns no `response` at all, "
         "even when `lyrics` is the only question; with the lyrics question included, the other six answers are lost too. `AI_PARSE_DOCUMENT` returns the full text of the same PDFs, so the lyrics value comes from it. "
         "The function below stands in for the course's model, `LYRICS_EXTRACTOR`: the six metadata questions go to `AI_EXTRACT`, the lyrics come from `AI_PARSE_DOCUMENT` (OCR mode), and the result is one object shaped like `AI_EXTRACT`'s own, `{error, response:{...7 values}}`. "
         "The lyrics value includes the title line and the credits at the foot of the page, because it is the whole page text."),
    sql("create_lyrics_extractor", "-- Substitute for the course's LYRICS_EXTRACTOR model (called here as a function, not with !PREDICT)\n" + DOC_CTX + LYRICS_FN),
    sql("extract_first_pdf", DOC_CTX + f"select to_varchar(ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.training_pdfs', 'Mary Had A Little Lamb by Storybooksong.pdf'),\n  responseFormat => {RESPONSE_FORMAT})) as extracted;"),
    update("Rewrite these four pages (4.4 to 4.6) as one `responseFormat` lab. Drop the lyrics-field instruction to \"delete two answers and edit the other\": AI_EXTRACT returns the lyrics as one value."),
    page("Continue Training the Model"),
    course("🧪 LAB: Load the Next Lyrics PDF and Use it to Keep Training Your Model (Beyond the Sea by Bobby Darin.pdf). *For us, only the last value was not correct. It was empty.*"),
    sql("extract_second_pdf", DOC_CTX + f"select to_varchar(ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.training_pdfs', 'Beyond the Sea by Bobby Darin.pdf'),\n  responseFormat => {RESPONSE_FORMAT})) as extracted;"),
    page("More PDFs for Training"),
    course("🧪 LAB: Download 4 More Files (September, Gloria, Fortnight, Cutie Pie). *The Snowflake Documentation suggests 20 training cases, but we'll just do 4 more.*"),
    sql("extract_four_more", DOC_CTX + "select relative_path,\n  to_varchar(ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.training_pdfs', relative_path),\n  responseFormat => " + RESPONSE_FORMAT + ")) as extracted\nfrom directory(@training_pdfs)\nwhere relative_path in ('September by Earth, Wind & Fire.pdf', 'Gloria by Laura Branigan.pdf', 'Fortnight by Taylor Swift.pdf', 'Cutie Pie by One Way.pdf');"),
    update("\"Suggests 20 training cases\" was Document AI model-build guidance and does not apply to AI_EXTRACT."),
]

# ---------------------------------------------------------------- lesson 5
NB["lesson_05_implementing_the_model"] = preamble("Lesson 5: Implementing Our ML Model", "The stage, RAW_SONGS, and processing the lyric PDFs.") + [
    page("Converting the Manual Training to Code"),
    course("🥋 LAB: Click the Train Model Button (15 to 45 minutes) (LLMM_161, 162). This turns the manual training into code applied to new PDFs."),
    update("There is no Train Model button and no wait. With AI_EXTRACT the extraction is available immediately, so the \"proceed to the next page while you wait\" framing goes away."),
    page("Test a File Against the Published Model"),
    course("🥋 LAB: Create a Stage for Your PDFs (LLMM_164, 165): stage **lyrics_pdfs** in DOC_AI_DB.DOC_AI_SCHEMA, directory table on, server-side encryption, created as DOC_AI_ROLE."),
    sql("create_lyrics_pdfs_stage", "-- SQL equivalent of the Create Stage dialog (LLMM_165)\n" + DOC_CTX + "create stage lyrics_pdfs\n  directory = (enable = true)\n  encryption = (type = 'SNOWFLAKE_SSE');"),
    course("🥋 LAB: Load a Lyrics PDF File Into Your Stage (The Girl From Ipanema by Amy Winehouse.pdf; LLMM_167)."),
    sql("load_ipanema", "-- SQL equivalent of **+ Files**\n" + DOC_CTX + copy_files("doc_ai_db.doc_ai_schema.lyrics_pdfs", [LESSON5[0]]) + "\nalter stage lyrics_pdfs refresh;\nlist @lyrics_pdfs;"),
    course("🥋 LAB: Run Some of the Code From the Model (LLMM_168, 169)."),
    note("The course's code reads `@LYRICS_PDF`, but the stage it just had the learner create is `lyrics_pdfs` (LLMM_165, and the screenshot LLMM_168 uses `@LYRICS_PDFS`). It also calls the model `LYRICS_EXTRACTOR!PREDICT`, which does not exist. It runs as written and reports the error."),
    sql("predict_as_given", DOC_CTX + "-- the course's block\n" + protected(code("Test a File Against the Published Model"))),
    sql("extract_ipanema", "-- Substitute: the LYRICS_EXTRACTOR function (AI_EXTRACT + AI_PARSE_DOCUMENT) in place of LYRICS_EXTRACTOR!PREDICT\n" + DOC_CTX + f"select ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.lyrics_pdfs', 'The Girl From Ipanema by Amy Winehouse.pdf'),\n  responseFormat => {RESPONSE_FORMAT}) as extracted;"),
    page("Preparing to Store the Model Output"),
    course("🎯 CHALLENGE LAB: Create a New Schema & Award Additional Privileges: USAGE for DOC_AI_ROLE on the SXGA2 database; new schema LYRICS in SXGA2 owned by SYSADMIN; USAGE on LYRICS for DOC_AI_ROLE; table RAW_SONGS in LYRICS with a single column JSON of type VARIANT, owned by SYSADMIN; INSERT and SELECT on RAW_SONGS for DOC_AI_ROLE (LLMM_171, 172)."),
    sql("create_lyrics_schema", "-- Derived solution\nuse role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\ngrant usage on database SXGA2 to role doc_ai_role;\ncreate schema SXGA2.LYRICS;\ngrant usage on schema SXGA2.LYRICS to role doc_ai_role;\n"
        "create table SXGA2.LYRICS.RAW_SONGS (json variant);\ngrant insert, select on table SXGA2.LYRICS.RAW_SONGS to role doc_ai_role;"),
    page("Process Files and Store the Output"),
    course("🥋 LAB: Add an Insert Command to the Select (LLMM_175), then view the inserted row (LLMM_176)."),
    sql("insert_ipanema", "-- Substitute for the course's `insert into sxga2.lyrics.raw_songs SELECT ...LYRICS_EXTRACTOR!PREDICT(...)`\n" + DOC_CTX + f"insert into sxga2.lyrics.raw_songs\nselect ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.lyrics_pdfs', 'The Girl From Ipanema by Amy Winehouse.pdf'),\n  responseFormat => {RESPONSE_FORMAT});"),
    sql("view_inserted_row", "select * from sxga2.lyrics.raw_songs;"),
    course("🎯 CHALLENGE LAB: Load and Process Three More Files (99 Red Balloons, Ribbon in the Sky, Flashdance... What a Feeling). Insert the results into your RAW lyrics table; a select should show 4 rows total."),
    sql("load_three_more", "-- SQL equivalent of **+ Files**\n" + DOC_CTX + copy_files("doc_ai_db.doc_ai_schema.lyrics_pdfs", LESSON5[1:]) + "\nalter stage lyrics_pdfs refresh;"),
    sql("insert_three_more", "-- Derived solution: the same insert for each file\n" + DOC_CTX + "insert into sxga2.lyrics.raw_songs\nselect ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.lyrics_pdfs', relative_path),\n  responseFormat => " + RESPONSE_FORMAT
        + ")\nfrom directory(@lyrics_pdfs)\nwhere relative_path in ('99 Red Balloons by Nena.pdf', 'Ribbon in the Sky by Stevie Wonder.pdf', 'Flashdance... What a Feeling by Irene Cara.pdf');"),
    sql("raw_songs_count", "select count(*) as rows_in_raw_songs from sxga2.lyrics.raw_songs;"),
    page("Parse the Stored JSON Song Data"),
    course("🥋 LAB: Parse the JSON Back into the Values we Defined. Run the select below (it parses the 7 value/questions), then the second select that splits each value's confidence score."),
    note("The course's selects read Document AI's shape (`json:song_title[0].value`, `.score`, `__documentMetadata:ocrScore`). AI_EXTRACT stores `{\"error\":null,\"response\":{\"song_title\":\"...\", ...}}`, so the course's selects run as written and return NULLs. The substitute reads the new shape and has no score columns."),
    sql("parse_json_as_given_1", code("Parse the Stored JSON Song Data", 0)),
    sql("parse_json_as_given_2", code("Parse the Stored JSON Song Data", 1)),
    sql("parse_json_substitute", "-- Substitute: the same seven values from the AI_EXTRACT output (no confidence scores exist)\nselect json:response:song_title::text as song_title\n    , json:response:performing_artist::text as performing_artist\n    , json:response:lyrics::text as song_lyrics\n"
        "    , json:response:authors::text as authors\n    , json:response:lyrics_copyright_holders::text as copyright_holders\n    , json:response:lyric_licensor_provider::text as licensor_provider\n    , json:response:source::text as source\nfrom sxga2.lyrics.raw_songs;"),
    update("Rewrite this page for the AI_EXTRACT output shape and remove the confidence-score discussion and LLMM_178. The 'stream and task pipeline' pointer refers to a Document AI tutorial; the equivalent now is a stream on the stage directory table with a task that calls AI_EXTRACT."),
]

# ---------------------------------------------------------------- lesson 6
NB["lesson_06_summarize"] = preamble("Lesson 6: The SUMMARIZE() Function", "Views over the extracted songs, SUMMARIZE and SENTIMENT, bulk processing from a stage folder.") + [
    page("Views for Exploring the SUMMARIZE() Function"),
    course("🥋 LAB: Convert the Select to a View (LLMM_180): `create view doc_ai_db.doc_ai_schema.parsed_song_data as` over the scored select, as DOC_AI_ROLE."),
    sql("create_parsed_song_data_as_given", "-- From screenshot LLMM_180 (the course's scored select)\n" + DOC_CTX + """create view doc_ai_db.doc_ai_schema.parsed_song_data as
select json:__documentMetadata:ocrScore as overall_confidence_score
    , json:song_title[0].score as song_title_score
    , json:song_title[0].value::text as song_title
    , json:performing_artist[0].score as perf_art_score
    , json:performing_artist[0].value::text as performing_artist
    , json:lyrics[0].score as lyrics_score
    , json:lyrics[0].value::text as song_lyrics
    , json:authors[0].score as authors_score
    , json:authors[0].value::text as authors
    , json:lyrics_copyright_holders[0].score as copyright_score
    , json:lyrics_copyright_holders[0].value::text as copyright_holders
    , json:lyric_licensor_provider[0].score as provider_score
    , json:lyric_licensor_provider[0].value::text as licensor_provider
    , json:source[0].score as source_score
    , json:source[0].value::text as source
  from sxga2.lyrics.raw_songs;"""),
    sql("create_parsed_song_data_substitute", "-- Substitute: the same view name and value columns over the AI_EXTRACT output (the score columns are dropped)\n" + DOC_CTX + """create or replace view doc_ai_db.doc_ai_schema.parsed_song_data as
select json:response:song_title::text as song_title
    , json:response:performing_artist::text as performing_artist
    , json:response:lyrics::text as song_lyrics
    , json:response:authors::text as authors
    , json:response:lyrics_copyright_holders::text as copyright_holders
    , json:response:lyric_licensor_provider::text as licensor_provider
    , json:response:source::text as source
  from sxga2.lyrics.raw_songs;"""),
    course("🥋 LAB: Give SYSADMIN Access to the View (LLMM_182, 183): USAGE on DOC_AI_DB and its schema, SELECT on the view."),
    sql("grant_sysadmin_view_access", "-- SQL equivalent of the Privileges dialogs (LLMM_182 shows the learner as ACCOUNTADMIN, the owner of DOC_AI_DB). Real ACCOUNTADMIN.\nuse role accountadmin;\ngrant usage on database doc_ai_db to role {{SYSADMIN_ROLE}};\ngrant usage on schema doc_ai_db.doc_ai_schema to role {{SYSADMIN_ROLE}};\n"
        "grant select on view doc_ai_db.doc_ai_schema.parsed_song_data to role {{SYSADMIN_ROLE}};"),
    note("In the course DOC_AI_DB is owned by ACCOUNTADMIN, who makes this grant (LLMM_182); DOC_AI_ROLE only received CREATE SCHEMA/MODIFY/USAGE, so it cannot pass USAGE on to another role. The cell therefore uses the real ACCOUNTADMIN."),
    course("📓 Differences in the Views: create a view for SYSADMIN that focuses on the data values, adding CORTEX.SUMMARIZE() and CORTEX.SENTIMENT()."),
    sql("song_summaries_as_given", "use role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\n" + protected(code("Views for Exploring the SUMMARIZE() Function"))),
    sql("song_summaries_substitute", "-- Substitute: ai_summarize and ai_sentiment (a label instead of a number)\nuse role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\ncreate or replace view sxga2.lyrics.song_summaries as\nselect song_title\n"
        "    , ai_summarize(song_lyrics) as song_summary\n    , ai_sentiment(song_lyrics):categories[0]:sentiment::text as song_sentiment\nfrom DOC_AI_DB.DOC_AI_SCHEMA.PARSED_SONG_DATA;"),
    sql("select_song_summaries", "select * from sxga2.lyrics.song_summaries;"),
    course("🎯 CHALLENGE LAB: Add & Process More Files. Upload the training songs to the stage (in a folder), then edit the insert statement (add the folder path) so each file is processed. Hints: you may need to change roles; use LS to list the files; one insert per file, including the directory in the file name."),
    sql("load_training_folder", "-- SQL equivalent of uploading to a folder named training (LLMM_185, 188)\n" + DOC_CTX + "copy files into @doc_ai_db.doc_ai_schema.lyrics_pdfs/training/\nfrom " + DOWNLOADS + "\nfiles = (" + TRAIN_LIST + ");\nalter stage lyrics_pdfs refresh;\nls @lyrics_pdfs/training;"),
    sql("insert_training_folder", "-- Derived solution (LLMM_187): the insert with the folder in the path\n" + DOC_CTX + "insert into sxga2.lyrics.raw_songs\nselect ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.lyrics_pdfs', relative_path),\n  responseFormat => " + RESPONSE_FORMAT + ")\nfrom directory(@lyrics_pdfs)\nwhere relative_path like 'training/%';"),
    sql("training_songs_summaries", "use role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\nselect * from sxga2.lyrics.song_summaries;"),
    page("Automating Processing & Testing Translation"),
    course("🎯 CHALLENGE LAB: Load the Final Set of PDFs: download and unzip More_songs.zip; upload the files into a new directory in your stage called \"automated\" (LLMM_189)."),
    sql("load_automated_folder", "-- SQL equivalent of the upload\n" + DOC_CTX + "copy files into @doc_ai_db.doc_ai_schema.lyrics_pdfs/automated/\nfrom " + DOWNLOADS + "\nfiles = (" + ", ".join("'" + n.replace("'", "''") + "'" for n in AUTOMATED) + ");\nalter stage lyrics_pdfs refresh;"),
    course("🥋 LAB: Run the Statements to See How RELATIVE_PATH can be used to bulk process the files."),
    sql("relative_path_statements", DOC_CTX + code("Automating Processing & Testing Translation", 0)),
    course("🥋 LAB: Process All Files in the Automated Folder (LLMM_191)."),
    sql("process_automated_as_given", DOC_CTX + protected(code("Automating Processing & Testing Translation", 1))),
    sql("process_automated_substitute", "-- Substitute: AI_EXTRACT per file in the folder\n" + DOC_CTX + "insert into sxga2.lyrics.raw_songs\nselect ai_extract(file => to_file('@doc_ai_db.doc_ai_schema.lyrics_pdfs', relative_path),\n  responseFormat => "
        + RESPONSE_FORMAT + ")\nfrom directory(@lyrics_pdfs)\nwhere relative_path like '%automated%';"),
    course("🥋 LAB: View Summaries for the Latest Batch of Songs (LLMM_193-195): compare the summaries and sentiment of songs in two languages."),
    sql("latest_batch_summaries", "use role {{SYSADMIN_ROLE}};\nuse warehouse {{WAREHOUSE}};\nselect * from sxga2.lyrics.song_summaries;"),
    sql("raw_songs_total", "select count(*) as rows_in_raw_songs from sxga2.lyrics.raw_songs;"),
    update("Sentiment: the course compares numeric scores between a song and its translation (\"quantify a significant change\"). With labels that comparison needs a different method (for example AI_COMPLETE scoring, or label counts per song)."),
]

# ---------------------------------------------------------------- lesson 7
BTS = code("Multi-Language & the Future of GenAI in Snowflake", 0)
BTS_JA = code("Multi-Language & the Future of GenAI in Snowflake", 1)


def bts_sub(code_text):
    m = re.search(r"select '(.*?)' as song_title\n, '(.*?)' as lyrics\n, snowflake\.cortex\.translate\(lyrics, '(\w+)', 'en'\)", code_text, re.S)
    title, lyrics, lang = m.groups()
    return (f"-- Substitute. AI_SUMMARIZE cannot take an AI_TRANSLATE result in the same query (\"Non-SQL UDF is not supported inside lambda expression\"),\n"
            f"-- so the translation is materialized first.\nuse schema SXGA2.LYRICS;\n"
            f"create or replace temporary table bts_{lang}_translated as\nselect '{title}' as song_title\n, '{lyrics}' as lyrics\n, ai_translate(lyrics, '{lang}', 'en') as eng_lyrics;\n"
            f"select song_title, lyrics, eng_lyrics\n, ai_summarize(eng_lyrics) as summary\n, ai_sentiment(eng_lyrics) as song_sentiment\nfrom bts_{lang}_translated;")


NB["lesson_07_wrapping_up"] = preamble("Wrapping Up", "Multi-language lyrics and the BTS examples.") + [
    page("Multi-Language & the Future of GenAI in Snowflake"),
    course("📓 Lyrics in Spanish, Summary in English? The new files are in languages other than English; the summarize function did the translation along with the summary (LLMM_198). 📓 Lyrics in Hangul? Hiragana? Nope. (LLMM_199). Run these two selects to see what might have been."),
    note(SUB_NOTE),
    sql("bts_korean_as_given", protected(BTS)),
    sql("bts_japanese_as_given", protected(BTS_JA)),
    sql("bts_korean_substitute", "-- Substitute: ai_translate / ai_summarize / ai_sentiment\n" + bts_sub(BTS)),
    sql("bts_japanese_substitute", "-- Substitute: ai_translate / ai_summarize / ai_sentiment\n" + bts_sub(BTS_JA)),
    update("The course's pattern `summarize(translate(...))` in one SELECT no longer works with the AI functions: `AI_SUMMARIZE(AI_TRANSLATE(...))` fails with \"Non-SQL UDF is not supported inside lambda expression\" (verified 2026-11-14). The translation has to be materialized (a temp table or CTAS) before summarizing."),
    update("The course says the Korean and Japanese PDFs 'did not fare as well' because of Document AI's language limits (LLMM_199). Tested 2026-11-14 with AI_EXTRACT + AI_PARSE_DOCUMENT: both BTS PDFs extract correctly (title, artist and full lyrics in Hangul and Japanese, see the query below), so that claim, the screenshot and the 'Hangul? Hiragana? Nope.' heading need to be rewritten."),
    sql("bts_extracted_rows", "select json:response:song_title::text as song_title, left(json:response:lyrics::text, 120) as lyrics_start\nfrom sxga2.lyrics.raw_songs where json:response:song_title::text ilike '%Blood%' or json:response:song_title::text ilike '%피%' or json:response:song_title::text ilike '%血%';"),
    md("Closing page: *More GenAI in Snowflake? Of course! Stay tuned for additional modules.* Nothing to run."),
    update("\"With our new AI CEO\" and the Bing Image Creator credit are dated; verify or remove."),
]

# ---------------------------------------------------------------- write
META = {"jupytext": {"main_language": "sql"}, "kernelspec": {"display_name": "Streamlit Notebook", "name": "streamlit"}}
for sub in ("data", "dora", "tools"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
for sub in ("", "dora"):
    for old in [f for f in os.listdir(os.path.join(OUT, sub)) if f.endswith(".ipynb")]:
        os.remove(os.path.join(OUT, sub, old))
for old in os.listdir(os.path.join(OUT, "data")):
    os.remove(os.path.join(OUT, "data", old))
for src, dst in PDF_NAMES.items():
    shutil.copy(os.path.join(ASSETS, src), os.path.join(OUT, "data", dst))
for n, b in zip_pdfs().items():
    open(os.path.join(OUT, "data", n), "wb").write(b)
_EXTRACT_RE = re.compile(r"(?:to_varchar\()?ai_extract\(file => (to_file\([^)]*\)),\s*responseFormat => \{[^}]*\}\)")
for cells in NB.values():
    for c in cells:
        if c["cell_type"] == "code" and c["metadata"].get("language") == "sql":
            c["source"] = re.sub(r"ai_extract\(file => (to_file\([^)]*\)),\s*responseFormat => \{[^}]*\}\)", r"lyrics_extractor(\1)", c["source"])
for name, cells in NB.items():
    names = [c["metadata"].get("name") for c in cells if c["cell_type"] == "code"]
    assert len(names) == len(set(names)), (name, [n for n in names if names.count(n) > 1])
    json.dump({"cells": cells, "metadata": META, "nbformat": 4, "nbformat_minor": 5},
              open(os.path.join(OUT, f"{name}.ipynb"), "w"), indent=1)
    print(f"{name:46s} cells={len(cells):3d}  code={len(names):3d}")
shutil.copy(os.path.abspath(__file__), os.path.join(OUT, "tools", os.path.basename(__file__)))
print("data files:", len(os.listdir(os.path.join(OUT, "data"))))
