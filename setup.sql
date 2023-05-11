CREATE TABLE docs(
    id SERIAL NOT NULL,
    created TIMESTAMP NOT NULL,
    iati_identifier VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    content_type VARCHAR,
    full_text VARCHAR,
    PRIMARY KEY (iati_identifier, source)
);
