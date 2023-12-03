#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import re
from json import loads, dumps, dump

import pandas as pd
from jinja2 import FileSystemLoader, Environment

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


def reader(config: dict):
    # with open("./log/nginx-access-ui.log-20170630", 'r') as f:
    with open(config.get("LOG_DIR") + "/nginx-access-ui.log-20170630", "r") as f:
        data = f.readlines()
    return data


def parse_log_line(line: str):
    log_pattern = re.compile(
        r'^(\S+) (\S+)  (\S+) \[([^\]]+)\] "(\S+)\s?(\S+)?\s?(\S+)?" (\d+) (\d+) "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)" (\S+) (\S+)'
    )
    match = log_pattern.match(line)
    if match:
        return match.groups()
    else:
        return None


def truncate_string(text, max_length=30):
    return text[:max_length] + ("..." if len(text) > max_length else "")


def main():
    d = reader(config)

    columns = [
        "$remote_addr",
        "$remote_user",
        "$http_x_real_ip",
        "$time_local",
        "$request_method",
        "$request_path",
        "$request_version",
        "$status",
        "$body_bytes_sent",
        "$http_referer",
        "$http_user_agent",
        "$http_x_forwarded_for",
        "$http_X_REQUEST_ID",
        "$http_X_RB_USER",
        "$request_time",
    ]

    data = [parse_log_line(line) for line in d[:] if line]

    df = pd.DataFrame(data, columns=columns)

    df["$time_local"] = pd.to_datetime(df["$time_local"], format="%d/%b/%Y:%H:%M:%S %z")
    df["$request_time"] = pd.to_numeric(df["$request_time"])

    count = df.groupby(by=["$request_path"])["$request_path"].count()
    count_sum = df.groupby(by=["$request_path"])["$remote_addr"].count().sum()
    count_perc = count / count_sum * 100

    time_sum = df.groupby(by=["$request_path"])["$request_time"].sum()
    time_tot = df.groupby(by=["$request_path"])["$request_time"].sum().sum()
    time_perc = time_sum / time_tot * 100

    time_avg = df.groupby(by=["$request_path"])["$request_time"].mean()
    time_max = df.groupby(by=["$request_path"])["$request_time"].max()
    time_med = df.groupby(by=["$request_path"])["$request_time"].median()

    frame = {
        "count": count,
        "count_perc": count_perc,
        "time_sum": time_sum,
        "time_perc": time_perc,
        "time_avg": time_avg,
        "time_max": time_max,
        "time_med": time_med,
    }

    df1 = pd.DataFrame(frame).sort_values(by="time_sum", ascending=False).head(1000)

    unparsed_json = (
        df1.reset_index()
        .rename(columns={"$request_path": "url"})
        .to_json(orient="records")
    )
    json_data_raw = loads(unparsed_json)
    json_data = json.dumps(json_data_raw)

    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("/report-template.html")

    rendered_html = template.render(json_data=json_data)

    with open("report.html", "w") as output_file:
        output_file.write(rendered_html)


if __name__ == "__main__":
    main()
