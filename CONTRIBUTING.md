# Contributing to AIMON

## Development Setup

```bash
git clone https://github.com/ALOKESHWARGOUD/AIMON.git
cd AIMON
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/
```

## Running the Demo

```bash
python examples/demo_leak_monitor.py
```

## Verify Install Works

```bash
pip install -e .
python -c "from aimon import AIMON; print('AIMON', __import__('aimon').__version__, 'installed OK')"
aimon --help
```

## Code Style

```bash
black aimon/ examples/ tests/
ruff check aimon/ examples/ tests/
```

## Project Structure

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for framework architecture.
See [docs/QUICKSTART.md](docs/QUICKSTART.md) for usage examples.
See [docs/PLUGINS.md](docs/PLUGINS.md) for extension guide.
