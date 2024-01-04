from pathlib import Path

from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="awpy",
    version="1.3.1",
    packages=find_packages(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "imageio~=2.33.1",
        "matplotlib~=3.8.0",
        "networkx~=3.1",
        "numpy>=1.26,<=1.27",
        "pandas~=2.1.1",
        "pydantic~=2.5.2",
        "scipy~=1.11.4",
        "Shapely~=2.0.2",
        "sphinx-rtd-theme==1.3",
        "sympy==1.12",
        "textdistance~=4.6.1",
        "tqdm~=4.66.1",
        "typing_extensions>=4.7.0,<5.0",
    ],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": [
            "*.go",
            "data/map/*.png",
            "data/map/*.json",
            "data/nav/*.txt",
            "data/nav/*.csv",
            "data/nav/*.json",
            "*.mod",
            "*.sum",
        ]
    },
    # metadata to display on PyPI
    author="Peter Xenopoulos",
    author_email="xenopoulos@nyu.edu",
    description=(
        "Counter-Strike: Global Offensive data parsing, "
        "analysis and visualization functions"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="esports sports-analytics csgo counter-strike",
    url="https://github.com/pnxenopoulos/awpy",
    project_urls={
        "Issues": "https://github.com/pnxenopoulos/awpy/issues",
        "Documentation": "https://awpy.readthedocs.io/en/latest/?badge=latest",
        "GitHub": "https://github.com/pnxenopoulos/awpy/",
    },
    classifiers=["License :: OSI Approved :: MIT License"],
)
