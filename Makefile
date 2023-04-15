.PHONY: refresh clean build release install test lint

refresh: lint clean build install

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov
	rm -rf coverage.xml
	rm *.matched
	rm *.pkl
	rm *._trees/
	# pip uninstall -y prev

build:
	python setup.py sdist bdist_wheel

release:
	python -m twine upload dist/*

install:
	python setup.py install --user

test:
	python -m unittest

lint:
	black prev/ tests/ --line-length 97 --preview
	flake8 prev/ tests/ --count --statistics --ignore=E501,W503
	# mypy --check-untyped-defs prev/
