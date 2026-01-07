.PHONY: test test-html test-cov clean install

install:
	pip install -e ".[dev]"

test:
	pytest

test-html:
	pytest --html=test-results/report.html --self-contained-html

test-cov:
	pytest --cov=src/agentbench --cov-report=html:htmlcov --cov-report=term-missing

test-all: test-html test-cov

clean:
	rm -rf htmlcov/
	rm -rf test-results/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

