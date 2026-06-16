## ADDED Requirements

### Requirement: Generic LLM analysis helper
`analyser.py` SHALL expose an internal helper `_analyse_with_model` that encapsulates the common pattern of calling the LLM, parsing JSON, validating against a Pydantic model, and returning a typed result or error tuple. All `analyse_*` public functions SHALL delegate to this helper instead of duplicating the try/except/log pattern.

#### Scenario: Successful analysis
- **WHEN** `_analyse_with_model` is called with a valid prompt and a Pydantic model class
- **THEN** it SHALL return `(model.model_dump(), None)`

#### Scenario: Pydantic validation failure
- **WHEN** the LLM returns JSON that fails Pydantic validation
- **THEN** it SHALL return `(None, str(validation_error))` and log the error with the provided context string

#### Scenario: LLM call failure
- **WHEN** the LLM call raises any exception
- **THEN** it SHALL return `(None, str(exception))` and log the error with the provided context string

### Requirement: filter_trivial_changes moved to analyser
`filter_trivial_changes` SHALL reside in `analyser.py`. `fetcher.py` SHALL NOT define or own this function. All callers SHALL import it from `analyser`.

#### Scenario: Import from analyser
- **WHEN** any module calls `filter_trivial_changes`
- **THEN** the import SHALL resolve from `src.analyser`

### Requirement: call_llm wrapper removed
The public wrapper `call_llm()` in `analyser.py` SHALL be removed. Direct callers (currently `security_advisories.py`) SHALL call `_call_mistral` directly or via the module-internal path.

#### Scenario: security_advisories uses direct LLM call
- **WHEN** `analyse_advisory` needs to call the LLM
- **THEN** it SHALL call `_call_mistral` directly without going through a redundant wrapper
