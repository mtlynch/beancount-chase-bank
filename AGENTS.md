## General

- Do not ask the user to run commands that you can run yourself.

## Creating a development environment

- See README.md for instructions on creating a development environment.

## Testing

- Run `./dev-scripts/build-python` after any change to verify that it has not caused regressions.

## Python testing

- Unit tests may not call private functions/methods (those prefixed with `_`)
- Unit tests may not use parameterized tests (e.g., `@pytest.mark.parametrize`).
  - This style of testing leads to tests that are difficult to verify by inspection.
