from setuptools import setup, find_packages

from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="awpy",
    version="1.1.7",
    packages=find_packages(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "pandas>=0.25.3",
        "numpy>=1.18.1",
        "scipy>=1.4.1",
        "matplotlib>=3.1.2",
        "networkx>=2.6.3",
        "textdistance>=4.2.0",
        "imageio>=2.9.0",
        "tqdm>=4.55.2",
    ],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": [
            "*.go",
            "data/map/*.png",
            "data/map/*.json",
            "data/nav/*.txt",
            "data/nav/*.csv",
            "*.mod",
            "*.sum",
        ]
    },
    # metadata to display on PyPI
    author="Peter Xenopoulos",
    author_email="xenopoulos@nyu.edu",
    description="Counter-Strike: Global Offensive data parsing, analysis and visualization functions",
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
