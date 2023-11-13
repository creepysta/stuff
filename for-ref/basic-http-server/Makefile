clean:
	@rm -rf build *.egg* dist

build: clean
	@python3 -m build --wheel

lint:
	@black . ;
	@isort --profile black .;
