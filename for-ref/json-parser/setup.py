from setuptools import setup

setup(
    name="json_parser",
    version="0.0.1",
    description="V. Basic Json Parser",
    author="creepysta",
    author_email="travisparker.thechoice93@gmail.com",
    py_modules=["json_parser"],
    python_requires=">=3.10",
    entry_points={"console_scripts": ["json_p = json_parser:main"]},
)
