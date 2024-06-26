from setuptools import setup

setup(
    name="literedis",
    version="0.0.1",
    description="small implementation of redis",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    py_modules=["literedis"],
    python_requires=">=3.10",
    entry_points={"console_scripts": ["literedis = literedis:main"]},
)
