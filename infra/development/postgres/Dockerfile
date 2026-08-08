FROM postgres:16.4

COPY infra/development/postgres/entrypoint.sh /usr/local/bin/dq-postgres-entrypoint
COPY infra/development/postgres/20-create-e2e-reader.sh /docker-entrypoint-initdb.d/20-create-e2e-reader.sh

RUN chmod 0755 /usr/local/bin/dq-postgres-entrypoint \
    /docker-entrypoint-initdb.d/20-create-e2e-reader.sh

ENTRYPOINT ["/usr/local/bin/dq-postgres-entrypoint"]
CMD ["postgres"]
