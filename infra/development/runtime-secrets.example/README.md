Create an ignored `runtime-secrets/data-sources/<reference>/` directory for each
development-only `secret://local/<reference>` value. Each directory contains
read-only `username` and `password` files. Never commit those files.

The live data-source E2E uses `secret://local/e2e-source`. Before the first
PostgreSQL initialization, create:

```text
runtime-secrets/data-sources/e2e-source/username  # exact value: dq_e2e_reader
runtime-secrets/data-sources/e2e-source/password  # a non-empty local-only password
```

Because the same read-only bind mount is consumed by the PostgreSQL and API
containers under different non-root users, these two development-only files must
be container-readable (for example mode `0444`); the directory remains ignored by
Git and must never be copied into an image.

The PostgreSQL image creates that unprivileged login from the mounted files and
generates a short-lived development TLS certificate. If the database volume was
initialized before these files existed, recreate the development volumes before
running the live acceptance test.
