SHELL := /bin/sh

.PHONY: dev build lint typecheck test test-python check check-all update-data update-data-dry archive-snapshot

dev:
	npm run dev

build:
	npm run build

lint:
	npm run lint

typecheck:
	npm run typecheck

test:
	npm run test

test-python:
	npm run test:python

check:
	npm run check

check-all:
	npm run check:all

update-data:
	python scripts/update_tips.py --write

update-data-dry:
	python scripts/update_tips.py --dry-run

archive-snapshot:
	@round=$$(grep -o '"round":[0-9]*' data/current_round_tips.json | head -1 | cut -d: -f2); \
	timestamp=$$(date +%Y-%m-%d); \
	cp data/current_round_tips.json "data/archive/$${timestamp}_round_$${round}.json"
	@echo "Snapshot archived."
