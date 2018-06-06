#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import os
import re
import gzip
import json
import argparse
import logging
from string import Template
from collections import namedtuple

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] '
#                     '"$request" $status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" '
#                     '"$http_X_RB_USER" $request_time';

config = {
    "REPORT_SIZE": 100,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./logs",
    "CONFIG_DEFAULT": "./log_analyzer.json",
    "SCRIPT_LOG": None,
    "SCRIPT_LOG_LEVEL": "INFO",
    "ERRORS_THRESHOLD_%": 10
}


def get_args():

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--config", type=str,
                           default=config["CONFIG_DEFAULT"],
                           help="use specific config with custom settings in json format")
    return argparser.parse_args()


def update_config(config_file, config):

    external_config = {}

    try:
        with open(config_file, 'r') as f:
            data = f.read()
    except Exception as e:
        print("ERROR: {}: {}".format(config_file, e))
        return config

    external_config = json.loads(data)
    config.update(external_config)

    return config


def setup_logger(config):
    logger = logging.getLogger(__name__)
    log_format = '[%(asctime)s] %(levelname).1s %(message)s'
    log_date_format = '%Y.%m.%d %H:%M:%S'

    logging.basicConfig(filename=config["SCRIPT_LOG"],
                        level=config["SCRIPT_LOG_LEVEL"],
                        format=log_format,
                        datefmt=log_date_format)

    return logger


def get_log_name(work_dir):
    date_re = re.compile(r"nginx-access-ui.log-(\d+)(.gz|.txt)?$")

    last_log = namedtuple('last_log', ['log_name', 'log_date'])
    log = last_log('', '')

    file_name = ''
    file_date = 0

    for f in os.listdir(work_dir):
        if os.path.isfile(os.path.join(work_dir, f)):
            match = date_re.search(f)
            if match:
                file_date_tmp = int(match.group(1))
                if file_date_tmp > file_date:
                    file_name = f
                    file_date = file_date_tmp

    if file_name:
        log = last_log(os.path.join(work_dir, file_name),
                       re.sub(r'(\d{4})(\d{2})(\d{2})', r'\1.\2.\3', str(file_date)))

    return log


def percentage(part, total):
    return (float(part)/total) * 100


def parser(file_stream, logger, errors_limit):
    result = {}
    time_total = 0
    records_num = 0
    bad_url = 0

    for line in file_stream:

        line = line.decode('utf-8')
        line_sp = line.split()

        if len(line_sp) < 7:
            bad_url += 1
            records_num += 1
            continue

        url = line_sp[6]
        request_time = line_sp[-1]

        if not re.match(r"^(^https?://|/).*", url):
            bad_url += 1
            records_num += 1
            continue

        url_data = result.get(url, {"count": 0, "timings": []})
        url_data["count"] += 1
        url_data["timings"].append(float(request_time))
        time_total += float(request_time)

        result[url] = url_data
        records_num += 1

    if percentage(bad_url, records_num) > errors_limit:
        logger.error("Parsing error threshold ({}%) reached".format(
            errors_limit))

    return result, records_num, time_total


def median(lst):
    n = len(lst)
    if n < 1:
        return None
    if n % 2 == 1:
        return sorted(lst)[n//2]
    else:
        return sum(sorted(lst)[n//2-1:n//2+1])/2.0


def generate_report_data(data, records_num, time_total):
    result = []

    for url in data:
        url_summary = {}
        url_data = data[url]

        url_summary["url"] = url
        url_summary["count"] = url_data["count"]
        url_summary["count_perc"] = round(
            percentage(url_data["count"], records_num), 2)
        url_summary["time_sum"] = round(
            sum(url_data["timings"]), 2)
        url_summary["time_perc"] = round(
            percentage(url_summary["time_sum"], time_total), 2)
        url_summary["time_avg"] = round(
            url_summary["time_sum"] / len(url_data["timings"]), 2)
        url_summary["time_max"] = round(
            max(url_data["timings"]), 2)
        url_summary["time_med"] = round(
            median(url_data["timings"]), 2)

        result.append(url_summary)

    result_sorted = sorted(result, key=lambda k: k["time_sum"], reverse=True)

    return result_sorted


def write_report(report_data, report_file, config):

    with open("report.html", "r") as f:
        report_template = Template(f.read().decode("utf-8"))

    report_json = json.dumps(report_data)
    report_template = report_template.substitute(table_json=report_json)

    if not os.path.exists(config["REPORT_DIR"]):
        os.makedirs(config["REPORT_DIR"])

    with open(report_file, 'w') as f:
        f.write(report_template.encode("utf-8"))


def main(config):

    args = get_args()

    if args.config:
        config = update_config(args.config, config)

    logger = setup_logger(config)

    log = get_log_name(config["LOG_DIR"])
    report_file = os.path.join(config["REPORT_DIR"],
                               'report-{}.html'.format(log.log_date))

    if not log.log_name:
        logger.info("No logs found")
        exit(0)

    if os.path.exists(report_file):
        logger.info("{} already parsed, report file name is: {}".format(
            log.log_name, report_file))
        exit(0)

    opener = gzip.open if log.log_name.endswith(".gz") else open

    with opener(log.log_name, "r") as log:
        raw_data, records_num, time_total = parser(
            log,
            logger,
            config["ERRORS_THRESHOLD_%"])

    report_data = generate_report_data(raw_data,
                                       records_num,
                                       time_total)

    write_report(report_data[:config["REPORT_SIZE"]],
                 report_file,
                 config)


if __name__ == "__main__":
    try:
        main(config)
    except KeyboardInterrupt:
        logging.exception("User interruption:")
    except Exception:
        logging.exception("There is an error while runing script:")
