from configparser import ConfigParser
import psycopg2


def config(filename: str = "database.ini", section: str = "postgresql") -> dict:
    parser: ConfigParser = ConfigParser()

    parser.read(filename)
    db = {}
    if parser.has_section(section):
        for key_val in parser.items(section):
            db[key_val[0]] = key_val[1]
    if not db.values():
        raise RuntimeError(f"Could not load database config in file '{filename}' in section '{section}'")

    return db


def connect(db_config):
    return psycopg2.connect(**db_config)