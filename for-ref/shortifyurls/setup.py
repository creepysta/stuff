from pathlib import Path

from setuptools import setup

setup(
    name="shortifyurls",
    version="0.0.1",
    description="A very lite async http server",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    py_modules=["shortifyurls"],
    python_requires=">=3.10",
    install_requires=Path("./requirements.txt").read_text().splitlines(),
    entry_points={"console_scripts": ["shortifyurls = shortifyurls:main"]},
)
