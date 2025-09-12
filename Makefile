.PHONY: test
test:
	echo "Make successful"

.PHONY: pre-install
pre-install:
	poetry config virtualenvs.in-project true
	poetry shell
	poetry install

.PHONY: add
add:
	poetry add $(package)

.PHONY: makemigrations
makemigrations:
	poetry run python manage.py makemigrations

.PHONY: migrate
migrate:
	poetry run python manage.py migrate

.PHONY: start
start:
	poetry run python manage.py runserver

.PHONY: start\:prod
start\:prod:
	poetry run python manage.py runserver 0.0.0.0:8000
