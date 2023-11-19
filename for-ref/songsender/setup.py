import os

from setuptools import setup

setup(
    name="songsender",
    version="0.0.1",
    description="Get youtube urls for song names",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    python_requires=">=3.10",
    packages=["songsender"],
    install_requires=[
        "youtube-dl",
        "beautifulsoup4",
        "requests",
        # f"litehttp @ http://localhost/{os.getcwd()}/local_wheels/litehttp-0.0.1-py3-none-any.whl",
    ],
    entry_points={"console_scripts": ["songsender = songsender.__main__:main"]},
)
