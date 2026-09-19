up:
	docker compose up --build
down:
	docker compose down -v
python-test:
	cd python-commander && pytest -q
java-test:
	cd java-sre && mvn test
eval:
	cd evals && python evaluate.py
