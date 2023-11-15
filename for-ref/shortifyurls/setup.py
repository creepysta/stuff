import os

from setuptools import setup

setup(
    name="shortifyurls",
    version="0.0.1",
    description="A very lite async http server",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    py_modules=["shortifyurls"],
    python_requires=">=3.10",
    install_requires=[
        "wheel",
        "redis",
        # f"litehttp @ http://localhost/{os.getcwd()}/local_wheels/litehttp-0.0.1-py3-none-any.whl",
    ],
    entry_points={"console_scripts": ["shortifyurls = shortifyurls:main"]},
)
