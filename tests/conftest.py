def pytest_addoption(parser):
    parser.addoption(
        "--no-prompts", action="store_true", default=False,
        help="Skip the tests which prompt the user for confirmation"
    )
    parser.addoption(
        "--mock-display", action="store_true", default=False,
        help="Mocks the display hardware in case you don't have an example handy"
    )
