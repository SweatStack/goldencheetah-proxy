.PHONY: build publish test serve

build:
	rm -rf dist
	uvx --from build pyproject-build --installer uv

publish: build
	uvx twine upload dist/*

test:
	uv run pytest

serve:
	sweatstack page serve
