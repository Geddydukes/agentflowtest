# Minimal Reference Benchmark

## Layout

- `config.py`: defines `RunConfig`.
- `tasks.jsonl`: benchmark tasks.
- `README.md`: execution instructions.

## Recommended Command

```bash
aft run --config path/to/config.py
```

## CI Gate Example

```bash
aft gate --run-a runs/baseline --run-b runs/candidate --max-regressions 0
```
