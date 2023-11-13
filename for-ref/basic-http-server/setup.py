from setuptools import setup

setup(
    name='litehttp',
    version='1.0',
    description='A very lite async http server',
    author='creepysta',
    author_email='travisparker.thechoice93@gmail.com',
    py_modules=["litehttp"],
    python_requires='>=3.10',
    install_requires=["wheel"],
    long_description=open('README.md').read(),
)
