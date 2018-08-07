all:
	$(MAKE) migrate
	$(MAKE) run

run:
	python manage.py runserver

run-all:
	python manage.py runserver 0.0.0.0:8000

migrate:
	python manage.py makemigrations sinaweb
	python manage.py migrate

count:
	# Get the number of commits, not using this for
	# anything other than progress tracking.
	git rev-list --all --count
