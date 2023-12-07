#!/usr/bin/env python
# -*- coding: utf-8 -*-

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import argparse
import datetime as DT
import gzip
import json
import logging
import os
import re
import sys

import pandas as pd
from jinja2 import Environment, FileSystemLoader

# logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s: %(message)s.",
    datefmt="%Y.%m.%d %H:%M:%S",
)


# uncaught exceptions catching
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.exception(
        "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = handle_exception

# default config
config = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}


def reader(config: dict):
    """
    Function for reading baseline log file
    :param config: dict
    :return: data (readlines()), report name
    """
    files = []
    log_prefix = "nginx-access-ui.log"
    date_pattern = re.compile(r"\d{8}")
    # get file names in LOG_DIR
    for file in os.listdir(config.get("LOG_DIR")):
        if log_prefix in file:
            files.append(file)
    if not bool(files):
        logging.info("The are no files to parse")
        exit(0)

    # file selection
    last_file = files[0]  # initial file name
    last_date = DT.datetime.min  # initial file date
    for name in files:
        match = date_pattern.search(name)
        if match:
            date_str = match.group()
            dt = DT.datetime.strptime(date_str, "%Y%m%d")
            if dt > last_date:
                last_file = name
                last_date = dt
        else:
            logging.info(f"Incorrect data suffix in log name: '{name}'")
            continue
    if last_date == DT.datetime.min:
        logging.info("The are no files to parse")
        exit(0)
    # report file name generation and check its existence
    report_name = "report-" + last_date.strftime("%Y.%m.%d") + ".html"
    if os.path.isdir(config.get("REPORT_DIR")) and report_name in os.listdir(
        config.get("REPORT_DIR")
    ):
        logging.info(
            f"The last Log file '{last_file}' has been already parsed to '{report_name}'"
        )
        exit(0)

    # file opening
    if last_file.endswith(".gz"):
        with gzip.open(
            config.get("LOG_DIR") + "/" + last_file, "rt", encoding="utf-8"
        ) as f:
            data = f.readlines()
    else:
        with open(
            config.get("LOG_DIR") + "/" + last_file,
            "rt",
            encoding="utf-8",
        ) as f:
            data = f.readlines()
    return data, report_name


def parse_log_line(line: str):
    """
    Function for single line parsing
    :param line: str
    :return: tuple of parsed data
    """
    log_pattern = re.compile(
        r'^(\S+) (\S+)  (\S+) \[([^\]]+)\] "(\S+)\s?(\S+)?\s?(\S+)?" (\d+) (\d+) "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)" (\S+) (\S+)'
    )
    match = log_pattern.match(line)
    if match:
        return match.groups()
    else:
        return None


def create_dataframe(strings: list) -> pd.DataFrame:
    """
    Summary DataFrame creation
    :param strings: list
    :return: dict
    """
    processed_treshold = 0.75
    strings_num = len(strings)
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

    data = [parse_log_line(line) for line in strings[:] if line]
    data_len = len(list(filter(lambda x: x is not None, data)))

    if data_len / strings_num > processed_treshold:
        df = pd.DataFrame(data, columns=columns)
    else:
        logging.error(
            f"Parsed lines below specified threshold - {round(data_len / strings_num * 100)}% parsed"
        )
        exit(1)

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

    df_new = pd.DataFrame(
        {
            "count": count,
            "count_perc": count_perc,
            "time_sum": time_sum,
            "time_perc": time_perc,
            "time_avg": time_avg,
            "time_max": time_max,
            "time_med": time_med,
        }
    )
    return df_new


def truncate_string(text, max_length=30):
    return text[:max_length] + ("..." if len(text) > max_length else "")


def load_config(config_path):
    """
    This function opens config file, read dict inside and return
    :param config_path:
    :return: dict
    """
    try:
        with open(config_path, "r") as config_file:
            file_config = json.load(config_file)
        return file_config
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.exception(f"Error loading config file:\n {e}")
        return {}


def main():
    # config file reading
    parser = argparse.ArgumentParser(
        description="Script with configuration file support"
    )
    parser.add_argument(
        "--config", help="Path to the configuration file", default="config.json"
    )
    args = parser.parse_args()

    config_path = args.config

    file_config = load_config(config_path)
    config.update(file_config)

    # log-file operations
    data, report_name = reader(config)
    frame = create_dataframe(data)
    df1 = frame.sort_values(by="time_sum", ascending=False).head(
        config.get("REPORT_SIZE")
    )

    # json is written to html-template report-template.html
    unparsed_json = json.loads(
        df1.reset_index()
        .rename(columns={"$request_path": "url"})
        .to_json(orient="records")
    )
    json_data = json.dumps(unparsed_json)
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("/static/html/report-template.html")
    rendered_html = template.render(json_data=json_data)

    # html-report creation
    try:
        with open(config.get("REPORT_DIR") + "/" + report_name, "w") as output_file:
            output_file.write(rendered_html)
        logging.info(f"File {report_name} has just been created")
    except FileNotFoundError:
        os.makedirs(config.get("REPORT_DIR"))
        with open(config.get("REPORT_DIR") + "/" + report_name, "w") as output_file:
            output_file.write(rendered_html)
        logging.info(f"File {report_name} has just been created")


if __name__ == "__main__":
    main()
