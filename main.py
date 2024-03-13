import zipfile
import requests
import random
import sys
import yaml
import os
import gnupg
from pymongo import MongoClient
from dateutil import parser
from datetime import datetime
from pathlib import Path


def argparse():
    args = list(sys.argv[1:])
    iterations = yaml.safe_load(open("config.yml"))["iterations"]
    if len(args) > 0:
        try:
            if len(args) > 1:
                for i in range(iterations):
                    main(i, int(args[0]), int(args[1]))
            else:
                for i in range(iterations):
                    main(i, max=int(args[0]))
        except Exception as e:
            print("Invalid arguments, running with default values.\n")
            for i in range(iterations):
                main(i)
    else:
        for i in range(iterations):
            main(i)


def main(iteration:int, min: int = 50_000, max: int = 200_000):
    results = random.randint(min, max)
    gpg = gnupg.GPG()
    with open(list(Path(yaml.safe_load(open("config.yml"))["pgp"]).glob('*.asc'))[0], "rb") as f:
        result = gpg.import_keys(f.read())
        print(result.results)
        gpg.trust_keys(result.fingerprints, "TRUST_ULTIMATE")

    url = f"http://{'host.docker.internal' if is_docker() else 'localhost'}:3000/api/?inc=name,id,dob&results={results}&nat=us"
    response = requests.get(url)
    data = response.json()
    c = get_mongo_client(data["info"]["seed"])
    try:
        c.insert_many(data["results"])
        zip = write_files(
            data["results"], f'LN{iteration + 1:08}_{datetime.now():%Y%m%d}_{get_type()}.txt'
        )
        pgp_file(zip, gpg)
    except Exception as e:
        print(e)

def pgp_file(file: Path, gpg: gnupg.GPG) -> Path:
    target = file.parent / f"{file.stem}.zip.pgp"
    if target.exists():
        target.unlink()
    with open(file, "rb") as f:  
        success = gpg.encrypt_file(
            f,
            recipients=["dp@dolaninfo.com"],
            output=target.resolve(),
            passphrase="dolanops",
        )
        print(success.ok)
    return target

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


def write_files(data, name="data.json") -> Path:
    n = Path(yaml.safe_load(open("config.yml"))["output"]) / name
    l = Path(yaml.safe_load(open("config.yml"))["output"]) / f"{n.stem}_LEXID.txt"
    with open(n.resolve(), "w") as f:
        with open(l.resolve(), "w") as lf:
            for ix, record in enumerate(data):
                f.write(f"{format_record(record, ix)}\n")
                lf.write(f"{ix:<28}{random.randint(5_000_000, 10_000_000):<15}{2356489:<28}\n")
            f.write("EOF")
    zip = zip_create(n, l)
    return zip

def zip_create(file: Path, lidfile: Path) -> Path:
    target = file.parent / f"{file.stem}_REQ.zip"
    with zipfile.ZipFile(target, "w") as z:
        z.write(file, arcname=file.name)
        z.write(lidfile, arcname=lidfile.name)
    return target

def format_record(record, ix) -> str:
    name = {k:v.strip() for k, v in record["name"].items()}
    id = record["id"]# {k:v.strip() for k, v  in record["id"].items()}
    dob = record["dob"]# {k:v.strip() for k, v in record["dob"].items()}
    return f'{format_ssn(id["value"])}{parser.parse(dob["date"]).strftime("%Y%m%d")}{name["last"]:<26}{name["first"]:<20}{ix:<28}{datetime.now():%Y%m%d}{" "*20}'


def format_ssn(string: str) -> str:
    return string.replace("-", "")

def get_type() -> str:
    return random.choices(["NONE", "CERT", "HITS"], [0.85, 0.15, 1/500], k=1)[0]


if __name__ == "__main__":
    argparse()
