"""Install packages as defined in this file into the Python environment."""
from setuptools import setup, find_packages


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="SeedrClient",
    author="Mr Developer X",
    author_email="139059229+Mr-Developer-X@users.noreply.github.com",
    description="A python library to interface with Seedr",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mr-Developer-X/seedr-client",
    package_dir={"": "src"},
    packages=find_packages(where="src", exclude=["tests"]),
    install_requires=[
        "setuptools>=45.0",
        "aria2p>=0.11.0",
        "requests>=2.30.0",  # Moved to newer version to jump over vulnerability in requests 2.29.0
        "torrentool>=1.2.0",
        "ih2torrent>=0.1.17;platform_system=='Linux'",
        "win-ih2torrent>=0.2.0;platform_system=='Windows'",
    ],
    keywords=["seedr", "bittorrent", "torrent", "magnet", "seedr api", "seedbox"],
    classifiers=[
        "Topic :: Utilities",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
)
