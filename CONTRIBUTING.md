# Contributing

RCA-Reuse is an ongoing research prototype. Contributions should preserve the distinction between measured results, implementation behavior, and future hypotheses.

Before changing code or experiments:

- read the relevant methodology and limitations documentation;
- preserve existing source, benchmark, and result artifacts unless a change is explicitly requested;
- do not add private datasets, proprietary RTL, credentials, or raw logs;
- document any changed assumptions, seeds, controls, or cost accounting;
- do not update headline metrics without a reproducible artifact and a clear evaluation scope.

For code changes, add or update focused tests where practical and run `python -m pytest`. For experiment changes, record the command, environment, simulator version, input manifest, and output location. Keep generated outputs out of Git unless they are small, reviewed, and approved for redistribution.

Pull requests should explain the research question affected, the behavioral change, the tests run, and any limitation or unresolved TODO introduced by the change.
