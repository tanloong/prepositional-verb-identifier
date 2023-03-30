.PHONY: refresh clean build release install test lint

refresh: lint clean build install

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf build
	rm -rf dist
	rm -rf vpe.egg-info
	rm -rf htmlcov
	rm -rf coverage.xml
	pip uninstall -y vpe

build:
	python setup.py sdist bdist_wheel

release:
	python -m twine upload dist/*

install:
	python setup.py install --user

test:
	python -m unittest

lint:
	black vpe/ tests/ --line-length 97 --preview
	flake8 vpe/ tests/ --count --max-line-length=97 --statistics
	mypy --check-untyped-defs vpe/
