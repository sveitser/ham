default:
    @just --list

test *args:
    pytest {{args}}

cov *args:
    pytest --cov=ham --cov-report=term-missing {{args}}

fmt *args:
    ruff format {{args}} .

lint *args:
    ruff check {{args}} .

check: fmt lint cov
