clean:
	@rm -rf build *.egg* dist .pytest_cache/ songsender/__pycache__ tests/__pycache__

build: lint clean
	@python3 -m build --wheel

lint:
	@black songsender/ tests/;
	@isort --profile black songsender/;
