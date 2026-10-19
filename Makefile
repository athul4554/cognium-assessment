.PHONY: up down logs reset db

up:        ## Build and start everything
	@test -f .env || cp .env.example .env
	docker compose up --build

down:      ## Stop everything
	docker compose down

logs:      ## Follow logs
	docker compose logs -f

reset:     ## Stop and wipe the database
	docker compose down -v

db:        ## Open a psql shell
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'
