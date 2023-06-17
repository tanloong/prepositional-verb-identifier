.PHONY: refresh clean build release install test lint

refresh: lint clean build install

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf src/prev/__pycache__
	rm -rf src/*.matched
	rm -rf src/*.json
	rm -rf build/
	rm -rf dist/
	rm -rf src/prev.egg-info
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -f *.json
	rm -rf *_trees
	rm -f *.matched

build:
	python setup.py sdist bdist_wheel

release:
	python -m twine upload dist/*

install:
	python setup.py install --user

test:
	python -m unittest

lint:
	black src/prev/ tests/ --line-length 97 --preview
	flake8 src/prev/ tests/ --count --statistics --ignore=E501,W503
	# mypy --check-untyped-defs prev/
