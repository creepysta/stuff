clean:
	@rm -rf build *.egg* dist __pycache__ 

build: clean lint 
	@python3 -m build --wheel

lint:
	@black . ;
	@isort --profile black .;
