import requests
import random
import sys
import yaml
import os
from pymongo import MongoClient
from dateutil import parser
from datetime import datetime
from pathlib import Path


def argparse():
    args = sys.argv[1:]
    iterations = yaml.safe_load(open("config.yml"))["iterations"]
    if len(args) > 0:
        try:
            if len(args) > 1:
                for _ in range(iterations):
                    main(int(args[0]), int(args[1]))
            else:
                for _ in range(iterations):
                    main(max=int(args[0]))
        except Exception as e:
            print("Invalid arguments, running with default values.\n")
            for _ in range(iterations):
                main()
    else:
        for _ in range(iterations):
            main()


def main(min: int = 1, max: int = 650):
    results = random.randint(min, max)
    url = f"https://randomuser.me/api/?inc=name,id,dob&results={results}&nat=us"
    response = requests.get(url)
    data = response.json()
    c = get_mongo_client(data["info"]["seed"])
    try:
        c.insert_many(data["results"])
        write_file(
            data["results"], f'{data["info"]["seed"]}_{datetime.now():%Y%m%d}.txt'
        )
    except Exception as e:
        print(e)


def is_docker():
    path = "/proc/self/cgroup"
    return (
        os.path.exists("/.dockerenv")
        or os.path.isfile(path)
        and any("docker" in line for line in open(path))
    )


def get_mongo_client(collection_name):
    env = "container" if is_docker() else "hardware"
    hostname = yaml.safe_load(open("config.yml"))["db"][env]["host"]
    client = MongoClient(hostname, 27017)
    db = client["RandomPeople"]
    collection = db[collection_name]
    return collection


def write_file(data, name="data.json"):
    n = Path(yaml.safe_load(open("config.yml"))["output"]) / name
    with open(n.resolve(), "w") as f:
        for ix, record in enumerate(data):
            f.write(f"{format_record(record, ix)}\n")
        f.write("EOF")


def format_record(record, ix) -> str:
    name = record["name"]
    id = record["id"]
    dob = record["dob"]
    return f'{format_ssn(id["value"])}{parser.parse(dob["date"]).strftime("%Y%m%d")}{name["last"]:<26}{name["first"]:<20}{ix:<28}{datetime.now():%Y%m%d}{" "*20}'


def format_ssn(string: str) -> str:
    return string.replace("-", "")


if __name__ == "__main__":
    argparse()
