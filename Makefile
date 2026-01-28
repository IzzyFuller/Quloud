.PHONY: mutate mutate-clean mutate-show mutate-html

# Run mutation testing (uses paths from pyproject.toml [tool.mutmut])
# Default config targets core modules (~2-5 min)
mutate:
	uv run mutmut run

# Clean mutation cache and re-run
mutate-clean:
	rm -rf .mutmut-cache mutants
	uv run mutmut run

# Show results summary
mutate-show:
	uv run mutmut results

# Generate HTML report
mutate-html:
	uv run mutmut html
	@echo "Report at html/index.html"

# Interactive browser for reviewing mutants
mutate-browse:
	uv run mutmut browse
