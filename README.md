# logslice

Fast log file slicer that filters by time range and severity without loading full files.

## Installation

```bash
pip install logslice
```

## Usage

```python
from logslice import slice_log

# Filter logs by time range and severity
results = slice_log(
    filepath="app.log",
    start="2024-01-15 08:00:00",
    end="2024-01-15 09:00:00",
    severity="ERROR"
)

for entry in results:
    print(entry)
```

You can also use the CLI:

```bash
logslice app.log --start "2024-01-15 08:00:00" --end "2024-01-15 09:00:00" --severity ERROR
```

### Options

| Option | Description |
|--------|-------------|
| `--start` | Start of the time range (inclusive) |
| `--end` | End of the time range (inclusive) |
| `--severity` | Minimum log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `--output` | Write results to a file instead of stdout |

## How It Works

logslice uses binary search on log timestamps to locate the relevant section of a file, avoiding the need to read the entire log into memory. This makes it significantly faster than `grep` or manual parsing on large log files.

## Requirements

- Python 3.8+

## License

This project is licensed under the [MIT License](LICENSE).