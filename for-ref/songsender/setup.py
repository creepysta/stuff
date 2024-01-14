from pathlib import Path

from setuptools import setup

setup(
    name="songsender",
    version="0.0.1",
    description="Get youtube urls for song names",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    python_requires=">=3.10",
    packages=["songsender"],
    install_requires=Path("./requirements.txt").read_text().splitlines(),
    entry_points={"console_scripts": ["songsender = songsender.__main__:main"]},
)
