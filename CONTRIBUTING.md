# Contributing

Use synthetic pages and mocked network responses. Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Cover changes to authorization, host boundaries, DNS results, redirects, robots policy, response limits, and output paths with tests. Keep browser masking, challenge handling, proxy rotation, cookie reuse, third-party captures, and external-service fixtures outside the package.
