init:
	@pip3 install -r requirements.dev.text

clean:
	@rm -rf build *.egg* dist __pycache__ .pytest_cache/

build: clean
	@python3 -m build --wheel

lint:
	@black . ;
	@isort --profile black .;
