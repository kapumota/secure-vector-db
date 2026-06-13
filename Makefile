.PHONY: clean clean-cache clean-build clean-reports clean-all

clean:
	python scripts/clean_project.py --cache --build

clean-cache:
	python scripts/clean_project.py --cache

clean-build:
	python scripts/clean_project.py --build

clean-reports:
	python scripts/clean_project.py --reports

clean-all:
	python scripts/clean_project.py --cache --build --reports
