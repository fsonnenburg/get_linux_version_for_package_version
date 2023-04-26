import sys

required_python = (3, 10)
if (sys.version_info.major, sys.version_info.minor) < required_python:
    raise RuntimeError(f"Need python {required_python[0]}.{required_python[1]}")

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass
import pprint
import re
from bs4 import BeautifulSoup
import certifi
import ssl
import urllib.request


@dataclass
class DistroInfo:
    name: str
    package_name: str
    required_package_version: str
    working_version: str = None
    not_working_version: str = None
    highest_version: str = None
    highest_package_version: str = None
    pretty_name: str = None


def parse_arguments():
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description="Get the first working version and the last not working version of "
        + "a linux distribution, fulfilling a special package version requirement, e.g, glibc 2.14",
    )
    parser.add_argument("package_name")
    parser.add_argument(
        "--distributions",
        default="centos,rocky,ubuntu,debian,opensuse",
        help="List of distributions to check",
    )
    parser.add_argument("--package_version")

    return parser.parse_args()


def get_associated_versions(info: DistroInfo):
    with urllib.request.urlopen(
        f"https://distrowatch.com/table.php?distribution={info.name}",
        context=ssl.create_default_context(cafile=certifi.where()),
    ) as response:
        html = response.read()

    soup = BeautifulSoup(html, "html.parser")
    info.pretty_name = soup.title.string.split(" ", 1)[1]

    distro_versions = []
    t = soup.find("th", string="Feature", recursive=True)
    if not t:
        raise RuntimeError(f"Couldn't find distribution ** {info.name} **")
    for td in t.parent.find_all("td"):
        distro_versions.append(" ".join(td.stripped_strings))

    package_versions = []
    t = soup.find("a", string=info.package_name, recursive=True)
    if not t:
        raise RuntimeError(f"Couldn't find package ** {info.package_name} **")
    for td in t.parent.parent.find_all("td"):
        package_versions.append(td.text)

    info._version_info = list(zip(package_versions, distro_versions))


def get_distro_info(info: DistroInfo):
    version_info = info._version_info
    if version_info:
        info.highest_package_version = version_info[0][0]
        info.highest_version = version_info[0][1]

    previous_distro_version = "--"
    if info.required_package_version is None:
        info.required_package_version = info.highest_package_version
    required_package_version = tuple(map(int, info.required_package_version.split(".")))
    for package_version_str, distro_version in version_info:
        if re.match(r"\d+\.\d.*", package_version_str):
            package_version = tuple(map(int, package_version_str.split(".")))
        else:
            break
        if package_version < required_package_version:
            info.not_working_version = distro_version
            info.working_version = previous_distro_version
            break
        else:
            previous_distro_version = distro_version

    return info


def check_distros(distro_names, package_name, required_package_version):
    for distro_name in distro_names.split(","):
        info = DistroInfo(distro_name, package_name, required_package_version)
        get_associated_versions(info)
        get_distro_info(info)
        pprint.pprint(info)


if __name__ == "__main__":
    args = parse_arguments()
    check_distros(args.distributions, args.package_name, args.package_version)
