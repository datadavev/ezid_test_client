import logging
import json
import ezid_query.ezidq
import click
import datetime
import dateparser

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""


def datetimeToJsonStr(dt):
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        # Naive timestamp, convention is this must be UTC
        return f"{dt.strftime(JSON_TIME_FORMAT)}Z"
    return dt.strftime(JSON_TIME_FORMAT)


def utcFromDateTime(dt, assume_local=True):
    # is dt timezone aware?
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        if assume_local:
            # convert local time to tz aware utc
            dt.astimezone(datetime.timezone.utc)
        else:
            # asume dt is in UTC, add timezone
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    # convert to utc timezone
    return dt.astimezone(datetime.timezone.utc)


def datetimeFromSomething(V, assume_local=True):
    if V is None:
        return None
    if isinstance(V, datetime.datetime):
        return utcFromDateTime(V, assume_local=assume_local)
    if isinstance(V, float) or isinstance(V, int):
        return utcFromDateTime(
            datetime.datetime.fromtimestamp(V), assume_local=assume_local
        )
    if isinstance(V, str):
        return utcFromDateTime(
            dateparser.parse(V, settings={"RETURN_AS_TIMEZONE_AWARE": True}),
            assume_local=assume_local,
        )
    return None


def httpDateToJson(d):
    if d is None:
        return d
    dt = datetimeFromSomething(d)
    return datetimeToJsonStr(dt)


def dtdsecs(t):
    return t.seconds + t.microseconds / 1000000.0


def pj(j):
    return json.dumps(j, indent=2)


def resSummary(res):
    r = {
        "status": res["status"],
        "elapsed": dtdsecs(res["elapsed"]),
        "url": res["url"],
        "total": res["results"]["total"],
        "count": len(res["results"]["records"])
    }
    return r


def runQuery(cli, params, manager=False):
    qform = cli.blankQueryForm(manager=False)
    qform.update(params)
    res = cli.search(qform)
    return res


def queries(cli, params):
    for ot in ezid_query.ezidq.EzidSearch.OBJECT_TYPES:
        q = params.copy()
        q["object_type"] = ot
        yield q


@click.command()
@click.option("--manager", is_flag=True, help="Use manage query form")
@click.option("--filtered", default="t", help="Hidden filtered value, 't'")
def main(manager, filtered):
    params = {"identifier": "ark:/87925/drs1.iberian.100191"}
    #params = {"keywords": "peregrin"}
    #params = {"filtered": filtered}
    cli = ezid_query.ezidq.EzidSearch()
    res = runQuery(cli, params, manager=manager)
    print(pj(resSummary(res)))
    return
    for q in queries(cli, params):
        res = runQuery(cli, q, manager=manager)
        print(pj(resSummary(res)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
