import logging
import time
import mysql.connector
import json
import click
import datetime

'''
Watch queries in mysql

dev:
ssh -L3306:rds-ias-ezid-search-dev.cmcguhglinoa.us-west-2.rds.amazonaws.com:3306 ezid-dev

stage:
ssh -L3306:rds-ias-ezid-search2-stg.cmcguhglinoa.us-west-2.rds.amazonaws.com:3306 ezid-stage2
'''

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""

@click.command()
@click.option("-s", "--seconds", default=5, help="Interval period")
@click.option("-u", "--user", default=None, help="DB user with priviledges")
@click.option("-p", "--passwd", default=None, help="DB password")
@click.option("-d", "--dbname", default="ezid", help="Database name")
def main(seconds, user, passwd, dbname):
    if seconds < 1:
        seconds = 1;
    if user is None or passwd is None:
        raise ValueError("user and passwd required")
    db = mysql.connector.connect(
        host="localhost",
        user=user,
        password=passwd,
        database=dbname
    )
    csr = db.cursor()
    Q = "SELECT current_schema, sql_text FROM performance_schema.events_statements_current"
    while True:
        csr.execute(Q)
        n = 0
        for row in csr.fetchall():
            if row[0] is not None:
                if row[1] != Q:
                    n += 1
                    print(row)
        if n > 0:
            print("---")
        time.sleep(seconds)

if __name__ == "__main__":
    main()
